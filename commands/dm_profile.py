"""
DM Profile management commands
Allows DMs to set and view their preferred display name
"""
import logging
import discord
from discord import app_commands

logger = logging.getLogger('xp-bot')


def setup_dm_profile_commands(bot, db, guild_id):
    """Register DM profile management commands"""

    @bot.tree.command(name="dm_profile_set", description="Set your preferred DM display name")
    @app_commands.describe(name="The name you want displayed when you DM quests")
    async def dm_profile_set(interaction: discord.Interaction, name: str):
        """Set the user's preferred DM display name"""
        dm_name = name.strip()

        if not dm_name:
            await interaction.response.send_message(
                "DM name cannot be empty.",
                ephemeral=True
            )
            return

        if len(dm_name) > 255:
            await interaction.response.send_message(
                "DM name must be 255 characters or less.",
                ephemeral=True
            )
            return

        try:
            await db.set_dm_profile(interaction.user.id, dm_name)
            await interaction.response.send_message(
                f"✅ Your DM profile has been updated!\n"
                f"Display Name: **{dm_name}**\n\n"
                f"This name will now appear on **all quests** where you are assigned as DM (past and present).",
                ephemeral=True
            )
            logger.info(f"User {interaction.user.id} set DM profile name to '{dm_name}'")

        except Exception as e:
            logger.error(f"Error setting DM profile: {e}")
            await interaction.response.send_message(
                "An error occurred while updating your DM profile.",
                ephemeral=True
            )

    @bot.tree.command(name="dm_profile_view", description="View your DM profile")
    async def dm_profile_view(interaction: discord.Interaction):
        """View the user's DM profile"""
        try:
            profile = await db.get_dm_profile(interaction.user.id)

            if not profile:
                await interaction.response.send_message(
                    "You don't have a DM profile set yet.\n"
                    "Use `/dm_profile_set` to set your preferred DM display name.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Your DM Profile",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Display Name",
                value=profile['preferred_dm_name'],
                inline=False
            )
            embed.add_field(
                name="Last Updated",
                value=profile['updated_at'].strftime('%B %d, %Y at %I:%M %p'),
                inline=False
            )
            embed.set_footer(text=f"User ID: {interaction.user.id}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error viewing DM profile: {e}")
            await interaction.response.send_message(
                "An error occurred while retrieving your DM profile.",
                ephemeral=True
            )
