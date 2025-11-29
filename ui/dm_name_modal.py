"""
DM Name Confirmation Modal
Allows DMs to confirm or customize their display name when being added to a quest
"""
import discord
import logging

logger = logging.getLogger('xp-bot')


class DMNameModal(discord.ui.Modal, title="Confirm Your DM Name"):
    """Modal for DM to confirm/customize their display name"""

    dm_name = discord.ui.TextInput(
        label="Your DM Display Name",
        placeholder="Enter the name you want displayed as DM",
        required=True,
        max_length=255
    )

    def __init__(self, db, quest_id: int, quest_name: str, user_id: int,
                 default_name: str, is_primary: bool = False):
        super().__init__()
        self.db = db
        self.quest_id = quest_id
        self.quest_name = quest_name
        self.user_id = user_id
        self.is_primary = is_primary

        # Set default value
        self.dm_name.default = default_name

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        dm_display_name = self.dm_name.value.strip()

        if not dm_display_name:
            await interaction.response.send_message(
                "DM name cannot be empty.",
                ephemeral=True
            )
            return

        try:
            # Add DM to quest with confirmed name
            await self.db.add_quest_dm(
                self.quest_id,
                self.user_id,
                dm_display_name,
                self.is_primary
            )

            # Update DM profile with this name as their preferred name
            await self.db.set_dm_profile(self.user_id, dm_display_name)

            dm_type = "Primary DM" if self.is_primary else "DM"
            await interaction.response.send_message(
                f"You've been added as {dm_type} to quest **{self.quest_name}**\n"
                f"Display Name: **{dm_display_name}**",
                ephemeral=True
            )

            logger.info(f"DM {self.user_id} confirmed name '{dm_display_name}' for quest {self.quest_id}")

        except Exception as e:
            logger.error(f"Error adding DM with confirmed name: {e}")
            await interaction.response.send_message(
                "An error occurred while adding you as DM.",
                ephemeral=True
            )
