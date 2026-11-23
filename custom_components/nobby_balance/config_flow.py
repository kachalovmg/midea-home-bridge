"""Configure the UART-to-TCP bridge."""

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT

from . import DOMAIN
from .protocol import BoilerClient


class NobbyBalanceConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().lower()
            port = user_input[CONF_PORT]
            if not host or any(char.isspace() for char in host) or "://" in host:
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                client = BoilerClient(host, port)
                try:
                    await client.read()
                except (OSError, TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title="Kentatsu Nobby Balance",
                        data={CONF_HOST: host, CONF_PORT: port},
                    )
                finally:
                    client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=5678): vol.All(int, vol.Range(min=1, max=65535)),
            }),
            errors=errors,
        )
