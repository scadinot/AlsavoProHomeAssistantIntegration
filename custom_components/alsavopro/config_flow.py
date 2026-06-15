"""Adds config flow for AlsavoPro pool heater integration."""
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_NAME,
    CONF_IP_ADDRESS,
    CONF_PORT
)

from .const import (
    SERIAL_NO,
    DOMAIN,
    CONNECTION_TYPE,
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_LOCAL,
    CLOUD_IP,
    CLOUD_PORT,
    DEFAULT_LOCAL_PORT,
)

# _LOGGER = logging.getLogger(__name__)

# Reject empty submissions for required text fields without needing
# dedicated error translation keys.
NON_EMPTY_STRING = vol.All(str, vol.Length(min=1))

CONNECTION_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONNECTION_TYPE, default=CONNECTION_TYPE_CLOUD): vol.In(
            [CONNECTION_TYPE_CLOUD, CONNECTION_TYPE_LOCAL]
        ),
    }
)

CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(SERIAL_NO): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

LOCAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(SERIAL_NO): str,
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_PORT, default=DEFAULT_LOCAL_PORT): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: core.HomeAssistant, name, serial_no, ip_address, port_no, password):
    """Validate the user input allows us to connect."""

    # Pre-validation for missing mandatory fields
    if not name:
        raise MissingNameValue("The 'name' field is required.")
    if not password:
        raise MissingPasswordValue("The 'password' field is required.")

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data[SERIAL_NO] == serial_no:
            raise AlreadyConfigured("A device with this serial number already exists.")

    # Additional validations (if any) go here...


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alsavo Pro pool heater integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step: choose connection type."""
        if user_input is not None:
            if user_input[CONNECTION_TYPE] == CONNECTION_TYPE_CLOUD:
                return await self.async_step_cloud()
            return await self.async_step_local()

        return self.async_show_form(
            step_id="user",
            data_schema=CONNECTION_TYPE_SCHEMA,
        )

    async def async_step_cloud(self, user_input=None):
        """Handle cloud connection configuration."""
        errors = {}

        if user_input is not None:
            try:
                name = user_input[CONF_NAME]
                serial_no = user_input[SERIAL_NO]
                password = user_input[CONF_PASSWORD].replace(" ", "")
                await validate_input(self.hass, name, serial_no, CLOUD_IP, CLOUD_PORT, password)
                unique_id = f"{name}-{serial_no}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=unique_id,
                    data={CONF_NAME: name,
                          SERIAL_NO: serial_no,
                          CONF_IP_ADDRESS: CLOUD_IP,
                          CONF_PORT: CLOUD_PORT,
                          CONF_PASSWORD: password},
                )

            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                errors["base"] = "connection_error"
            except MissingNameValue:
                errors["base"] = "missing_name"

        return self.async_show_form(
            step_id="cloud",
            data_schema=CLOUD_SCHEMA,
            errors=errors,
        )

    async def async_step_local(self, user_input=None):
        """Handle local connection configuration."""
        errors = {}

        if user_input is not None:
            try:
                name = user_input[CONF_NAME]
                serial_no = user_input[SERIAL_NO]
                ip_address = user_input[CONF_IP_ADDRESS]
                port_no = user_input[CONF_PORT]
                password = user_input[CONF_PASSWORD].replace(" ", "")
                await validate_input(self.hass, name, serial_no, ip_address, port_no, password)
                unique_id = f"{name}-{serial_no}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=unique_id,
                    data={CONF_NAME: name,
                          SERIAL_NO: serial_no,
                          CONF_IP_ADDRESS: ip_address,
                          CONF_PORT: port_no,
                          CONF_PASSWORD: password},
                )

            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                errors["base"] = "connection_error"
            except MissingNameValue:
                errors["base"] = "missing_name"

        return self.async_show_form(
            step_id="local",
            data_schema=LOCAL_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow mirroring the initial setup (all fields editable)."""

    def __init__(self, config_entry):
        # Stored under a private name to avoid clashing with the read-only
        # `config_entry` property provided by recent Home Assistant versions.
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """First step: choose the connection type (defaults to the current one)."""
        data = self._config_entry.data
        current_type = (
            CONNECTION_TYPE_CLOUD
            if data.get(CONF_IP_ADDRESS) == CLOUD_IP
            else CONNECTION_TYPE_LOCAL
        )

        if user_input is not None:
            if user_input[CONNECTION_TYPE] == CONNECTION_TYPE_CLOUD:
                return await self.async_step_cloud()
            return await self.async_step_local()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONNECTION_TYPE, default=current_type): vol.In(
                    [CONNECTION_TYPE_CLOUD, CONNECTION_TYPE_LOCAL]
                ),
            }),
        )

    async def async_step_cloud(self, user_input=None):
        """Edit cloud connection settings."""
        data = self._config_entry.data

        if user_input is not None:
            return self._apply(
                user_input[CONF_NAME],
                user_input[SERIAL_NO],
                CLOUD_IP,
                CLOUD_PORT,
                user_input[CONF_PASSWORD].replace(" ", ""),
            )

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=data.get(CONF_NAME)): NON_EMPTY_STRING,
                vol.Required(SERIAL_NO, default=data.get(SERIAL_NO)): NON_EMPTY_STRING,
                vol.Required(CONF_PASSWORD, default=data.get(CONF_PASSWORD)): NON_EMPTY_STRING,
            }),
        )

    async def async_step_local(self, user_input=None):
        """Edit local connection settings."""
        data = self._config_entry.data
        is_local = data.get(CONF_IP_ADDRESS) != CLOUD_IP

        if user_input is not None:
            return self._apply(
                user_input[CONF_NAME],
                user_input[SERIAL_NO],
                user_input[CONF_IP_ADDRESS],
                user_input[CONF_PORT],
                user_input[CONF_PASSWORD].replace(" ", ""),
            )

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=data.get(CONF_NAME)): NON_EMPTY_STRING,
                vol.Required(SERIAL_NO, default=data.get(SERIAL_NO)): NON_EMPTY_STRING,
                vol.Required(
                    CONF_IP_ADDRESS,
                    default=data.get(CONF_IP_ADDRESS) if is_local else "",
                ): NON_EMPTY_STRING,
                vol.Required(
                    CONF_PORT,
                    default=data.get(CONF_PORT) if is_local else DEFAULT_LOCAL_PORT,
                ): NON_EMPTY_STRING,
                vol.Required(CONF_PASSWORD, default=data.get(CONF_PASSWORD)): NON_EMPTY_STRING,
            }),
        )

    def _apply(self, name, serial_no, ip_address, port_no, password):
        """Persist the new settings to the entry and finish the flow."""
        # The serial number is the device's stable identifier
        # (device_info uses ``(DOMAIN, serial_no)``), so reject a serial
        # already used by a *different* entry.
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if (entry.entry_id != self._config_entry.entry_id
                    and entry.data.get(SERIAL_NO) == serial_no):
                return self.async_abort(reason="already_configured")

        new_unique_id = f"{name}-{serial_no}"
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            title=new_unique_id,
            unique_id=new_unique_id,
            data={
                CONF_NAME: name,
                SERIAL_NO: serial_no,
                CONF_IP_ADDRESS: ip_address,
                CONF_PORT: port_no,
                CONF_PASSWORD: password,
            },
            options={},  # purge any password stored by the previous options flow
        )
        return self.async_create_entry(title="", data={})


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate host is already configured."""


class MissingNameValue(exceptions.HomeAssistantError):
    """Error to indicate name is missing."""


class MissingPasswordValue(exceptions.HomeAssistantError):
    """Error to indicate name is missing."""
