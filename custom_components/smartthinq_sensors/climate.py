"""Platform for LGE climate integration."""
from .wideq.device import DeviceType
from .wideq.ac import AirConditionerDevice, ACMode

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LGEDevice
from .const import DOMAIN, LGE_DEVICES

HVAC_MODE_LOOKUP = {
    ACMode.AI.name: HVAC_MODE_AUTO,
    ACMode.HEAT.name: HVAC_MODE_HEAT,
    ACMode.DRY.name: HVAC_MODE_DRY,
    ACMode.COOL.name: HVAC_MODE_COOL,
    ACMode.FAN.name: HVAC_MODE_FAN_ONLY,
    ACMode.ACO.name: HVAC_MODE_HEAT_COOL,
}
HVAC_MODE_REVERSE_LOOKUP = {v: k for k, v in HVAC_MODE_LOOKUP.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up LGE device climate based on config_entry."""
    entry_config = hass.data[DOMAIN]
    lge_devices = entry_config.get(LGE_DEVICES)
    if not lge_devices:
        return

    lge_climates = []
    lge_climates.extend(
        [
            LGEACClimate(lge_device, lge_device.device)
            for lge_device in lge_devices.get(DeviceType.AC, [])
        ]
    )

    async_add_entities(lge_climates)


class LGEClimate(CoordinatorEntity, ClimateEntity):
    """Base climate device."""

    def __init__(self, device: LGEDevice):
        """Initialize the climate."""
        super().__init__(device.coordinator)
        self._api = device
        self._name = device.name

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self._api.device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._api.available


class LGEACClimate(LGEClimate):
    """Air-to-Air climate device."""

    def __init__(self, device: LGEDevice, ac_device: AirConditionerDevice) -> None:
        """Initialize the climate."""
        super().__init__(device)
        self._device = ac_device

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._api.unique_id}-AC"

    @property
    def name(self):
        """Return the display name of this entity."""
        return self._name

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temperature."""
        return self._device.target_temperature_step

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        mode = self._api.state.operation_mode
        if not self._api.state.is_on or mode is None:
            return HVAC_MODE_OFF
        return HVAC_MODE_LOOKUP.get(mode)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_OFF:
            await self._device.power(False)
            return

        operation_mode = HVAC_MODE_REVERSE_LOOKUP.get(hvac_mode)
        if operation_mode is None:
            raise ValueError(f"Invalid hvac_mode [{hvac_mode}]")

        if self.hvac_mode == HVAC_MODE_OFF:
            await self._device.power(True)
        await self._device.set_op_mode(operation_mode)

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes."""
        return [HVAC_MODE_OFF] + [
            HVAC_MODE_LOOKUP.get(mode)
            for mode in self._device.op_modes
            if mode in HVAC_MODE_LOOKUP
        ]

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self._api.state.current_temp

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self._api.state.target_temp

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        await self._device.set_target_temp(
            kwargs.get("temperature", self.target_temperature)
        )

    @property
    def fan_mode(self) -> str:
        """Return the fan setting."""
        return self._api.state.fan_speed

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._device.set_fan_speed(fan_mode)

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._device.fan_speeds

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FAN_MODE | SUPPORT_TARGET_TEMPERATURE  # | SUPPORT_SWING_MODE

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.power(True)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.power(False)

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        min_value = self._device.target_temperature_min
        if min_value is not None:
            return min_value

        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        max_value = self._device.target_temperature_max
        if max_value is not None:
            return max_value

        return DEFAULT_MAX_TEMP
