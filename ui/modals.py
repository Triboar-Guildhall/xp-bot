"""
Discord UI modals for XP Bot configuration
"""
import discord
from utils.validation import validate_char_per_rp, validate_daily_cap, validate_xp_amount


class XPSettingsModal(discord.ui.Modal, title="Configure RP Settings"):
    """Modal for configuring RP XP settings"""
    char_per_rp = discord.ui.TextInput(label="Characters per XP (RP)", placeholder="240", required=True)
    daily_rp_cap = discord.ui.TextInput(label="Daily RP XP Cap", placeholder="5", required=True)

    def __init__(self, db, guild_id):
        super().__init__()
        self.db = db
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            char_per_rp_val = int(self.char_per_rp.value)
            daily_rp_cap_val = int(self.daily_rp_cap.value)

            # Validate char_per_rp
            is_valid, error_msg = validate_char_per_rp(char_per_rp_val)
            if not is_valid:
                await interaction.response.send_message(f"❌ Characters per XP: {error_msg}", ephemeral=True)
                return

            # Validate daily_rp_cap
            is_valid, error_msg = validate_daily_cap(daily_rp_cap_val)
            if not is_valid:
                await interaction.response.send_message(f"❌ Daily RP cap: {error_msg}", ephemeral=True)
                return

            await self.db.update_config(
                self.guild_id,
                char_per_rp=char_per_rp_val,
                daily_rp_cap=daily_rp_cap_val
            )
            await interaction.response.send_message("✅ RP settings updated.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter valid numbers.", ephemeral=True)
