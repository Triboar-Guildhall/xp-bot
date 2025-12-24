"""
Discord UI views and dropdowns for XP Bot configuration
"""
import discord
from ui.modals import XPSettingsModal


class ChannelDropdown(discord.ui.Select):
    """Dropdown for selecting channels"""

    def __init__(self, label, target_key, bot, db, guild_id, current_channel_ids=None):
        self.target_key = target_key
        self.bot = bot
        self.db = db
        self.guild_id = guild_id
        current_channel_ids = current_channel_ids or []

        options = [
            discord.SelectOption(
                label=ch.name,
                value=str(ch.id),
                default=(ch.id in current_channel_ids)
            )
            for ch in bot.get_all_channels() if isinstance(ch, discord.TextChannel)
        ]
        super().__init__(
            placeholder=f"Select {label} channels...",
            min_values=0,
            max_values=min(25, len(options)),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        channel_ids = [int(v) for v in self.values]
        if self.target_key == "rp_channels":
            await self.db.update_config(self.guild_id, rp_channels=channel_ids)
        await interaction.response.send_message(f"✅ Updated `{self.target_key}`.", ephemeral=True)


class ChannelSettingsView(discord.ui.View):
    """View for channel selection dropdowns"""

    def __init__(self, bot, db, guild_id, current_rp_channels=None):
        super().__init__(timeout=None)
        self.add_item(ChannelDropdown("RP", "rp_channels", bot, db, guild_id, current_rp_channels))

    @classmethod
    async def create(cls, bot, db, guild_id):
        """Factory method to create view with current config loaded"""
        config = await db.get_config(guild_id)
        current_rp_channels = config.get("rp_channels", [])
        return cls(bot, db, guild_id, current_rp_channels)


class XPSettingsView(discord.ui.View):
    """Main settings view with buttons for different configuration options"""

    def __init__(self, bot, db, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.db = db
        self.guild_id = guild_id

    @discord.ui.button(label="RP Settings", style=discord.ButtonStyle.primary)
    async def rp_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(XPSettingsModal(self.db, self.guild_id))

    @discord.ui.button(label="Channel Settings", style=discord.ButtonStyle.secondary)
    async def channel_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = await ChannelSettingsView.create(self.bot, self.db, self.guild_id)
        await interaction.response.send_message(
            "Choose channels to enable XP tracking:",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Settings view closed.", ephemeral=True)
        self.stop()
