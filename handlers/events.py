"""
Event handlers for XP Bot - handles on_ready and on_message
"""
import os
import logging
import discord
from utils.xp import should_reset_xp, perform_daily_reset, get_level_and_progress

logger = logging.getLogger('xp-bot')


def setup_events(bot, db, guild_id):
    """Register event handlers with the bot"""

    @bot.event
    async def on_ready():
        logger.info(f"Bot '{bot.user.name}' is online")

        # Connect to database
        await db.connect()
        await db.initialize_schema()

        env = os.getenv("ENV", "prod")
        guild_id_env = os.getenv("GUILD_ID")

        if env == "dev" and guild_id_env:
            logger.info("Environment: development")
            guild = discord.Object(id=int(guild_id_env))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} slash commands to dev guild {guild_id_env}")
        else:
            logger.info("Environment: production")

            # Clear any old guild-specific commands from production bot
            if guild_id_env:
                guild = discord.Object(id=int(guild_id_env))
                bot.tree.clear_commands(guild=guild)
                await bot.tree.sync(guild=guild)
                logger.info(f"Cleared guild-specific commands from guild {guild_id_env}")

            # Sync global commands
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} global slash commands")

        logger.info("Available slash commands:")
        for cmd in bot.tree.get_commands():
            logger.info(f"  /{cmd.name}")

    @bot.event
    async def on_message(message):
        """Check each message to see if it should be awarded RP XP"""
        config = await db.get_config(guild_id)

        # RP tracking (user messages)
        if not message.author.bot and message.channel.id in config.get("rp_channels", []):
            user_id = message.author.id
            await db.ensure_user(user_id)

            # Check if we need to reset daily caps
            if await should_reset_xp(db, user_id):
                await perform_daily_reset(db, user_id)

            # Get active character
            active_char = await db.get_active_character(user_id)
            if not active_char:
                return

            # Add to character buffer
            char_buffer = active_char['char_buffer'] + len(message.content)

            # Calculate XP from buffer
            char_per_rp = config.get('char_per_rp', 240)
            potential_xp = char_buffer // char_per_rp
            xp_remaining = config.get('daily_rp_cap', 5) - active_char['daily_xp']
            gained_xp = min(potential_xp, xp_remaining)

            # Update buffer remainder
            new_buffer = char_buffer % char_per_rp

            # Award XP if any gained
            if gained_xp > 0:
                xp_result = await db.award_xp(
                    user_id,
                    active_char['name'],
                    gained_xp,
                    daily_xp_delta=gained_xp,
                    char_buffer_delta=new_buffer - active_char['char_buffer']
                )

                # Check for level-up and send notifications
                if xp_result['leveled_up']:
                    old_level = xp_result['old_level']
                    new_level = xp_result['new_level']
                    new_xp = xp_result['new_xp']
                    char_name = active_char['name']

                    # Get updated character info
                    updated_char = await db.get_character(user_id, char_name)

                    # Send level-up notification to log channel
                    log_channel_id = await db.get_log_channel()
                    if log_channel_id:
                        log_channel = bot.get_channel(log_channel_id)
                        if log_channel:
                            from ui.character_view import DEFAULT_CHARACTER_IMAGE
                            level_embed = discord.Embed(
                                title=f"🎉 Level Up! - {char_name}",
                                description=f"**{char_name}** has leveled up from **Level {old_level}** to **Level {new_level}**!",
                                color=discord.Color.gold(),
                                timestamp=discord.utils.utcnow()
                            )

                            level_embed.add_field(
                                name="**Player**",
                                value=f"<@{user_id}>",
                                inline=True
                            )

                            level_embed.add_field(
                                name="**Old Level**",
                                value=str(old_level),
                                inline=True
                            )

                            level_embed.add_field(
                                name="**New Level**",
                                value=str(new_level),
                                inline=True
                            )

                            level_embed.add_field(
                                name="**Source**",
                                value="Roleplay Activity",
                                inline=False
                            )

                            # Add character sheet link if available
                            if updated_char.get('character_sheet_url'):
                                level_embed.add_field(
                                    name="**Character Sheet**",
                                    value=f"[View Sheet]({updated_char['character_sheet_url']})",
                                    inline=False
                                )

                            level_embed.add_field(
                                name="**Action Required**",
                                value="Please update your character sheet to reflect your new level!",
                                inline=False
                            )

                            # Add character image
                            image_url = updated_char.get("image_url") or DEFAULT_CHARACTER_IMAGE
                            level_embed.set_thumbnail(url=image_url)

                            try:
                                await log_channel.send(embed=level_embed)
                                logger.info(f"Posted level-up notification for {char_name} to log channel")
                            except Exception as e:
                                logger.error(f"Failed to post RP level-up notification: {e}")

                    # Send DM to character owner
                    try:
                        owner = await bot.fetch_user(user_id)

                        # Create rich embed for level-up DM
                        from ui.character_view import DEFAULT_CHARACTER_IMAGE
                        levelup_dm_embed = discord.Embed(
                            title=f"🎉 Level Up! - {char_name}",
                            description=f"**{char_name}** has leveled up from **Level {old_level}** to **Level {new_level}**!",
                            color=discord.Color.gold(),
                            timestamp=discord.utils.utcnow()
                        )

                        levelup_dm_embed.add_field(
                            name="**Player**",
                            value=f"<@{user_id}>",
                            inline=False
                        )

                        levelup_dm_embed.add_field(
                            name="**Old Level**",
                            value=str(old_level),
                            inline=True
                        )

                        levelup_dm_embed.add_field(
                            name="**New Level**",
                            value=str(new_level),
                            inline=True
                        )

                        levelup_dm_embed.add_field(
                            name="**New Total XP**",
                            value=f"{new_xp:,}",
                            inline=False
                        )

                        levelup_dm_embed.add_field(
                            name="**Source**",
                            value="Roleplay Activity",
                            inline=False
                        )

                        if updated_char.get('character_sheet_url'):
                            levelup_dm_embed.add_field(
                                name="**Action Required**",
                                value=f"Please update your [character sheet]({updated_char['character_sheet_url']}) to reflect your new level!",
                                inline=False
                            )
                        else:
                            levelup_dm_embed.add_field(
                                name="**Action Required**",
                                value="Please update your character sheet to reflect your new level!",
                                inline=False
                            )

                        # Add character image
                        image_url = updated_char.get("image_url") or DEFAULT_CHARACTER_IMAGE
                        levelup_dm_embed.set_thumbnail(url=image_url)

                        await owner.send(embed=levelup_dm_embed)
                        logger.info(f"Sent level-up DM to user {user_id}")
                    except Exception as e:
                        logger.warning(f"Could not send RP level-up DM to user {user_id}: {e}")

            elif new_buffer != active_char['char_buffer']:
                # Just update buffer
                await db.update_character_buffer(user_id, active_char['name'], new_buffer)

        await bot.process_commands(message)
