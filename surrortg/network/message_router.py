"""This module implements different types of message routing strategies."""
import logging
import asyncio
from ..inputs.input import Input
from dataclasses import dataclass

SRC_GAME_ENGINE = "gameEngine"
EVENT_NEW_PEER = "newPeer"
EVENT_PEER_LEFT = "peerLeft"
EVENT_ENABLE_ROUTING = "enableRouting"
EVENT_DISABLE_ROUTING = "disableRouting"
EVENT_GAME_CONTROLS = "gameControls"
EVENT_PING = "ping"
EVENT_ROBOT_LOG = "robotLog"


@dataclass
class InputBinding:
    dev: Input
    admin: bool


class MessageRouter:
    """Basic message router that routes a command to the correct input.

    Messages are routed to inputs based on input type and id.
    Following message format is expected:
    ::

        {
            payload:
            {
                type:    <input type>,
                id:      <input id>,
                command: <input specific command object>
            }
        }

    Additional fields may be present and will be ignored.
    """

    def __init__(self):
        self.inputs = {}
        self.reset_tasks = {}

    async def handle_message(self, msg, seat):
        """Routes a message according to input type and id.

        Reads type and id from message and lookups corresponding route from
        registered routes.

        If route is not found or message is malformed, warning is logged and
        nothing is done.

        :param msg: Message from game engine
        :type msg: dict
        :param seat: Robot seat
        :type seat: int
        """

        # We received a message from peer. Reset watchdog
        if msg.src != SRC_GAME_ENGINE:
            self._watchdog_reset(seat)

        if msg.event == EVENT_PING:
            return

        try:
            input_id = msg.payload["id"]
        except KeyError:
            logging.warning(f"Could not route message: malformed message")
            return

        if input_id in self.inputs:
            if self.inputs[input_id].admin:
                if not msg.isAdmin:
                    logging.warning(f"Non-admin trying to use admin input")
                    return
            await self.inputs[input_id].dev._on_input(
                msg.payload["command"], seat
            )
            return
        else:
            logging.warning(
                f"Seat {seat} received input from an unregistered "
                f"source: '{input_id}'.\nSeat {seat}'s current "
                f"registered inputs: {list(self.inputs.keys())}.\n"
                f"self.io.register_inputs({{'{input_id}':<INPUT>}}) "
                f"can be used to register this input."
            )

    def register_input(self, dev_id, dev, admin):
        """Registers a callback for route

        :param dev_id: Input device id
        :type dev_id: str
        :param dev: Input device
        :type dev: Input
        :param admin: Describes if the input is for admin use only
        :type admin: bool
        """
        self.inputs[dev_id] = InputBinding(dev, admin)

    def _watchdog_reset(self, seat):
        """Reset watchdog for the specified seat

        Creates a new reset task if none is previously defined for
        the specified seat.
        :param seat: Robot seat
        :type seat: int
        """
        if seat in self.reset_tasks:
            reset_task = self.reset_tasks[seat]
            if reset_task is not None and not reset_task.cancelled():
                self.reset_tasks[seat].cancel()
        self.reset_tasks[seat] = asyncio.create_task(self._reset_all(seat))

    async def _reset_all(self, seat):
        """Resets all inputs for the specified seat after the reset time

        :param seat: Robot seat
        :type seat: int
        """
        await asyncio.sleep(5)
        for route in self.inputs.values():
            await route.dev.reset(seat)
        logging.info(f"All inputs resetted for seat {seat}")


class MultiSeatMessageRouter:
    """Routes messages to correct seat based on sender.

    Messages are routed to seats (message routers) based on the sender.
    Following message format is expected:
    ::

        {
            event: <event>
            dst: <recipient id>
            src: <sender id> (optional)
            seat: <robot seat> (optional)
            payload: (optional)
                {
                    type:    <input type>,
                    id:      <input id>,
                    command: <input specific command object>
                }
            isAdmin: <boolean> (optional)
        }

    Additional fields may be present and will be ignored.

    `src` field value `gameEngine` is a special value meaning that our game
    engine has sent the message. If gameEngine wants to send a message to
    specific seat, `seat` field can be used for that.

    :param robot_log_handler: functions that handles robot logs
    :type robot_log_handler: function
    """

    def __init__(self, robot_log_handler):
        self.router = MessageRouter()
        self.route_mappings = {"gameEngine": "gameEngine"}
        self.seats_enabled = {}
        self.robot_log_handler = robot_log_handler

    async def handle_message(self, msg):
        """Handles a message.

        This function either
            1) Handles newPeer/peerLeft events by modifying routing.
            2) Forwards a game engine message to seat using `seat` field.
            3) Forwards a peer message using `src` field and current routing.
            4) Drops a message and logs warning if none of the above apply.
        """

        if msg.event == EVENT_ROBOT_LOG:
            self.robot_log_handler(msg)
        elif msg.src == SRC_GAME_ENGINE and msg.event != EVENT_GAME_CONTROLS:
            await self.handle_routing_messages(msg)
        elif msg.src in self.route_mappings:
            seat = self.route_mappings[msg.src]
            if msg.src == SRC_GAME_ENGINE or seat in self.seats_enabled:
                if (
                    msg.src == SRC_GAME_ENGINE
                    or msg.isAdmin
                    or self.seats_enabled[seat]
                ):
                    await self.router.handle_message(msg, seat)
            else:
                logging.warning(
                    f"Seat route registered but enabled status not defined. "
                    f"Message not handled: {msg}"
                )
        else:
            logging.warning(f"Received unhandleable peer message: {msg}")

    def register_input(self, dev_id, dev, admin=False):
        """Registers a new routing

        :param dev_id: Input device id
        :type dev_id: str
        :param dev: Input device
        :type dev: Input
        :param admin: Describes if the input is for admin use only,
        defaults to False
        :type admin: bool, optional
        """
        self.router.register_input(dev_id, dev, admin)

    async def handle_routing_messages(self, msg):
        """Handle routing related game engine messages

        :param msg: Message from game engine
        :type msg: dict
        :return: 'True' if the message was handled, 'False' otherwise
        :rtype: bool
        """
        if msg.event == EVENT_NEW_PEER and msg.payload is not None:
            if "seat" in msg.payload:
                seat = msg.payload["seat"]
            else:
                logging.warning(
                    f"Registering new route failed, seat not found "
                    f"for new peer on msg: {msg}"
                )
                return True
            self.route_mappings[msg.payload["id"]] = seat
            if seat not in self.seats_enabled:
                self.seats_enabled[seat] = False
            logging.info(
                f"Registered route {msg.payload['id']}->"
                f"{msg.payload['seat']}"
            )
        elif msg.event == EVENT_PEER_LEFT and msg.payload is not None:
            try:
                seat = self.route_mappings[msg.payload["id"]]
                del self.route_mappings[msg.payload["id"]]
                logging.info(f"Removed route from {msg.payload['id']}")
            except KeyError:
                logging.warning("Trying to remove non-existing route")
                return True
        elif msg.event == EVENT_ENABLE_ROUTING:
            if msg.payload is not None and "seat" in msg.payload:
                self.set_enabled_seat(msg.payload["seat"], True)
                logging.info(f"Enabling routing for {msg.payload['seat']}")
            else:
                logging.info("Enabling routing for everything")
                self.set_enabled_all(True)
        elif msg.event == EVENT_DISABLE_ROUTING:
            if msg.payload is not None and "seat" in msg.payload:
                self.set_enabled_seat(msg.payload["seat"], False)
                logging.info(f"Disabling routing for {msg.payload['seat']}")
            else:
                logging.info("Disabling routing for everything")
                self.set_enabled_all(False)
        else:
            return False

        return True

    def set_enabled_all(self, enabled):
        """Sets message routing states for all seats

        :param enabled: State to set the routings to
        :type enabled: bool
        """
        for seat in self.seats_enabled:
            self.seats_enabled[seat] = enabled

    def set_enabled_seat(self, seat, enabled):
        """Sets message routing states for the specified seat

        :param seat: Robot seat
        :type seat: int
        :param enabled: State to set the routings to
        :type enabled: bool
        """
        self.seats_enabled[seat] = enabled

    def get_all_seats(self):
        """Returns all the seats that have routings set

        :return: All the seats that have routings set
        :rtype: list[int]
        """
        return self.seats_enabled