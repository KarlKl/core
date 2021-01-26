"""Support for EnOcean switches."""
import logging

import voluptuous as vol

from homeassistant.components import enocean
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_ID, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)

CONF_SENDER_ID = "sender_id"

CONF_CHANNEL = "channel"
DEFAULT_NAME = "EnOcean Switch"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SENDER_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the EnOcean switch platform."""
    channel = config.get(CONF_CHANNEL)
    dev_id = config.get(CONF_ID)
    dev_name = config.get(CONF_NAME)
    sender_id = config.get(CONF_SENDER_ID)

    add_entities([EnOceanSwitch(dev_id, dev_name, channel, sender_id)])


class EnOceanSwitch(enocean.EnOceanDevice, ToggleEntity):
    """Representation of an EnOcean switch device."""

    def __init__(self, dev_id, dev_name, channel, sender_id):
        """Initialize the EnOcean switch device."""
        super().__init__(dev_id, dev_name)
        self._light = None
        self._on_state = False
        self._on_state2 = False
        self.channel = channel
        self._sender_id = sender_id

    @property
    def is_on(self):
        """Return whether the switch is on or off."""
        return self._on_state

    @property
    def name(self):
        """Return the device name."""
        return self.dev_name

    def turn_on(self, **kwargs):
        """Turn on the switch."""
        optional = [0x03]
        optional.extend(self.dev_id)
        optional.extend([0xFF, 0x00])
        _LOGGER.debug("Dev ID: %s", self.dev_id)
#        self.send_command(
#            data=[0xd2, 0x4, 0x60, 0xe4, 0x5, 0x8, 0x2c, 0x37, 0x0],
#            optional=[0x1, 0xff, 0xff, 0xff, 0xff, 0x4c, 0x0],
#            packet_type=0x01,
#        )
# working
#        self.send_command(
#            data=[0xd2, 0x1, 0x0, 0x64, 0xff, 0x99, 0x87, 0x1, 0x80],
#            optional=[0x2, 0x5, 0x8, 0x2c, 0x37, 0x2d, 0x0],
#            packet_type=0x01,
#        )
        command = [0xD2, 0x01, self.channel & 0xFF, 0x64]
        command.append(self._sender_id)
        command.append([0x00])
        self.send_command(
            data=command,#[0xD2, 0x01, self.channel & 0xFF, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00],#[0xD2, 0x01, self.channel & 0xFF, 0x64, 0xff, 0x99, 0x87, 0x01, 0x00],#[0xD2, 0x01, self.channel & 0xFF, 0x64, 0x0>
            optional=optional,#[0x2, 0x5, 0x8, 0x2c, 0x37, 0x2d, 0x0],#optional,
            packet_type=0x01,
        )
        self._on_state = True

    def turn_off(self, **kwargs):
        """Turn off the switch."""
        optional = [0x03]
        optional.extend(self.dev_id)
        optional.extend([0xFF, 0x00])
        self.send_command(
            data=[0xD2, 0x01, self.channel & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],#[0xD2, 0x01, self.channel & 0xFF, 0x00, 0xff, 0x99, 0x87, 0x1, 0x00],
            optional=optional,#[0x2, 0x5, 0x8, 0x2c, 0x37, 0x2d, 0x0],#optional,
            packet_type=0x01,
        )
        self._on_state = False

    def value_changed(self, packet):
        """Update the internal state of the switch."""
        if packet.data[0] == 0xA5:
            # power meter telegram, turn on if > 10 watts
            packet.parse_eep(0x12, 0x01)
            if packet.parsed["DT"]["raw_value"] == 1:
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                watts = raw_val / (10 ** divisor)
                if watts > 1:
                    self._on_state = True
                    self.schedule_update_ha_state()
        elif packet.data[0] == 0xD2:
            # actuator status telegram
            packet.parse_eep(0x01, 0x01)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    self._on_state = output > 0
                    self.schedule_update_ha_state()

