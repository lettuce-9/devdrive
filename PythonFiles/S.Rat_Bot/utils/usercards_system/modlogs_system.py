import discord
from discord import app_commands, Interaction, Embed, ui
from discord.ext import commands, tasks
from typing import Optional
from datetime import datetime, timedelta
import asyncio
import os
import json
import copy

class Warn4ActionView(discord.ui.View):
    def __init__(self, cog, moderator: discord.Member, target: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.moderator = moderator
        self.target = target

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message("You are not authorized to use these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.guild.ban(self.target, reason="Reached 4 warnings")
            await interaction.followup.send(f"{self.target.mention} has been **banned**.")
        except Exception as e:
            await interaction.followup.send(f"Failed to ban user: {e}", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.primary)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.guild.kick(self.target, reason="Reached 4 warnings")
            await interaction.followup.send(f"{self.target.mention} has been **kicked**.")
        except Exception as e:
            await interaction.followup.send(f"Failed to kick user: {e}", ephemeral=True)

    @discord.ui.button(label="Timeout 1hr", style=discord.ButtonStyle.primary)
    async def timeout_1hr(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            until = discord.utils.utcnow() + timedelta(hours=1)
            await self.target.timeout(until, reason="Reached 4 warnings")
            await interaction.followup.send(f"{self.target.mention} has been **timed out** for 1 hour.")
        except Exception as e:
            await interaction.followup.send(f"Failed to timeout user: {e}", ephemeral=True)

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.success)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            print("Failed to dismiss:", e)

class ModLogsSystem(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.mod_logs = {}
        self.load_logs()
        self.cleanup_expired_warns.start()

    def clean_expired_warns_for_user(self, user_id: str):
        now = datetime.now()
        logs = self.mod_logs.get(user_id, [])
        new_logs = []

    def add_log(self, user_id, log_str, expires_at=None):
        user_id = str(user_id)
        if user_id not in self.mod_logs:
            self.mod_logs[user_id] = []

        now_utc = datetime.now()
        now_local = now_utc + timedelta(hours=8)

        entry = {
            "type": "warn",
            "content": f"Warn {len(self.mod_logs[user_id])+1}: {log_str}",
            "log": f"{log_str} on {now_local.strftime('%Y-%m-%d %H:%M:%S')}",
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S") if expires_at else None
        }

        self.mod_logs[user_id].append(entry)
        self.save_logs()

    def save_logs(self):
        with open("mod_logs.json", "w") as f:
            json.dump(self.mod_logs, f, indent=4)

    def load_logs(self):
        if os.path.exists("mod_logs.json"):
            try:
                with open("mod_logs.json", "r") as f:
                    self.mod_logs = json.load(f)
                    self.clean_expired_timeouts()
            except json.JSONDecodeError:
                print("Error decoding JSON from mod_logs.json.")
                self.mod_logs = {}
        else:
            self.mod_logs = {}
            print("mod_logs.json not found, initializing an empty log.")

    def clean_expired_timeouts(self):
        now = datetime.now()
        changed = False
        for user_id, logs in list(self.mod_logs.items()):
            new_logs = []
            for log in logs:
                if "Timed out until" in log:
                    try:
                        parts = log.split("Timed out until ")[1].split(" by")[0]
                        expiry_time = datetime.strptime(parts, "%Y-%m-%d %H:%M:%S")
                        if now > expiry_time:
                            changed = True
                            continue
                    except Exception:
                        pass
                new_logs.append(log)
            self.mod_logs[user_id] = new_logs
        if changed:
            self.save_logs()

    @tasks.loop(minutes=1)
    async def cleanup_expired_warns(self):
        print("[Worker-WarnCleanup, modlogs_system] Running expired warn cleanup...")
        now = datetime.now()
        changed = False

        for user_id, logs in list(self.mod_logs.items()):
            new_logs = []
            for log in logs:
                if isinstance(log, dict) and log.get("type") == "warn":
                    expires_at = log.get("expires_at")
                    if expires_at:
                        try:
                            expiry = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                            if now >= expiry:
                                print(f"[Worker-WarnCleanup, modlogs_system] Removing expired warn for user {user_id}")
                                changed = True
                                continue
                        except Exception as e:
                            print(f"[Worker-WarnCleanup, modlogs_system] Failed to parse expires_at: {e}")
                new_logs.append(log)
            self.mod_logs[user_id] = new_logs

        if changed:
            self.save_logs()
            print("[Worker-WarnCleanup, modlogs_system] Expired warns removed and logs saved.")


    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(
        user="User to warn",
        duration="Duration of the warn [1d, 7d, 0 for permanent]",
        reason="Reason for warning",
        offense="Message offense"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        duration: str,
        reason: str = "No reason provided",
        offense: Optional[str] = None
    ):
        print(f"[DEBUG] Received warn command from {interaction.user} for {user} with duration '{duration}'.")
    
        def parse_duration(duration_str: str) -> Optional[datetime]:
            if duration_str.strip() == "0":
                return None
            units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            try:
                num = int(duration_str[:-1])
                unit = duration_str[-1].lower()
                if unit not in units:
                    return None
                delta = timedelta(**{units[unit]: num})
                return datetime.now() + delta
            except (ValueError, IndexError) as e:
                print(f"[DEBUG] Failed to parse duration '{duration_str}': {e}")
                return None
            
        def format_duration(expires_at: Optional[datetime], now: datetime) -> str:
            if not expires_at:
                return "Permanent"
        
            delta = expires_at - now
            seconds = int(delta.total_seconds())
        
            days, seconds = divmod(seconds, 86400)
            hours, seconds = divmod(seconds, 3600)
            minutes, _ = divmod(seconds, 60)
        
            parts = []
            if days: parts.append(f"{days}d")
            if hours: parts.append(f"{hours}h")
            if minutes: parts.append(f"{minutes}m")
            return " ".join(parts) if parts else "Less than 1 minute"
        
    
        expires_at = parse_duration(duration)
        await interaction.response.defer(ephemeral=True)
        print("[DEBUG] Defered early.")
        if expires_at:
            print(f"[DEBUG] Parsed expiration time: {expires_at}")
        elif duration == "0":
            print("[DEBUG] Duration is 0, permanent warning.")
        else:
            embed = discord.Embed(
                title="Invalid Integer",
                description="Invalid duration. The correct durations are `10m, 1h, 7d, 0 for permanent`.",
                color=discord.Color.red()
            )      
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print("[DEBUG] Invalid duration provided. Sending error response.")
            return
    
        mod_role_ids = [1367831532240371722]
        print("[DEBUG] Checking moderator permissions...")
        if not any(role.id in mod_role_ids for role in interaction.user.roles):
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print("[DEBUG] Permission denied.")
            return
        print("[DEBUG] Moderator permission granted.")
    
        # await interaction.response.defer(ephemeral=True)
        # print("[DEBUG] Interaction deferred.")
    
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_logs = self.mod_logs.get(str(user.id), [])
        print(f"[DEBUG] Fetched user logs: {user_logs}")
    
        warn_number = sum(
            1 for log in user_logs
            if isinstance(log, dict) and log.get("type") == "warn"
        ) + 1

        print(f"[DEBUG] Calculated warn number: {warn_number}")
    
        log_entry = f"Warn {warn_number}: Warned by {interaction.user} for: {reason} on {now}"
        print(f"[DEBUG] Final log entry: {log_entry}")
        self.add_log(user.id, log_entry, expires_at=expires_at)
        print(f"[DEBUG] Log added for user {user.id}")
    
        print(f"[DEBUG] warn_number check: {warn_number}")
        sent_mod_action = False

        if warn_number >= 4:
            print("[DEBUG] Triggering mod action UI.")
            member = interaction.guild.get_member(user.id)
            print(f"[DEBUG] Fetched member: {member}")
            if member:
                print(f"[DEBUG] Target user is a guild member. Prompting action view.")
                view = Warn4ActionView(self, interaction.user, member)
                embed = discord.Embed(
                    title="Alert",
                    description=f"{user.mention} has reached **4 warnings.** Choose what action to take below:",
                    color=discord.Color.orange()
                )
                try:
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    print("[DEBUG] Warn action view sent.")
                    sent_mod_action = True
                except Exception as e:
                    print(f"[ERROR] Failed to send warn action view: {e}")
        
        if not sent_mod_action:
            now = datetime.now()
            expires_at = parse_duration(duration)
            duration_str = format_duration(expires_at, now)

            unix_ts = int(now.timestamp())

            embed = discord.Embed(
                title="Warning Issued",
                description=(
                    f"{user.mention} has been warned.\n"
                    f"Duration: **{duration_str}**\n"
                    f"Issued at: <t:{unix_ts}:f> • <t:{unix_ts}:R>"
                ),
                color=discord.Color.orange()
            )

            await interaction.followup.send(embed=embed, ephemeral=False)
            print("[DEBUG] Warning embed sent.")
    
        if offense:
            print(f"[DEBUG] Attempting to fetch message for offense ID: {offense}")
            try:
                msg = await interaction.channel.fetch_message(int(offense))
                jump_url = msg.jump_url
                print("[DEBUG] Message found. Added jump URL.")
            except Exception as e:
                print(f"[DEBUG] Failed to fetch message: {e}")
                jump_url = f"https://discord.com/channels/{interaction.guild.id}/{interaction.channel.id}/{offense}"
    
            embed.add_field(name="Message Offense", value=f"[Jump to Message]({jump_url})", inline=False)

    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(user="User to timeout", duration="Duration in minutes", reason="Reason for timeout")
    async def timeout(self, interaction: discord.Interaction, user: discord.User, duration: int, reason: str = "No reason provided"):
        mod_role_ids = [1367831532240371722]
        is_mod = any(role.id in mod_role_ids for role in interaction.user.roles)

        if not is_mod:
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        member = interaction.guild.get_member(user.id)
        if not member:
            embed = discord.Embed(
                title="Error",
                description=f"User is not in this guild.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        try:
            until = discord.utils.utcnow() + timedelta(minutes=duration)
            await member.timeout(until, reason=reason)
        except Exception as e:
            await interaction.response.send_message(f"Failed to timeout: {e}", ephemeral=True)
            print(f"An error occured trying to warn the target user : {e}")
            print(f"Bot's top role: {interaction.guild.me.top_role.position}")
            print(f"Target's top role: {member.top_role.position}")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"Timed out by {interaction.user} for {duration} minutes: {reason} on {now}"
        self.add_log(user.id, log_entry)

        embed = discord.Embed(
            title="Timeout Issued",
            description=f"{user.mention} has been timed out for `{duration} minutes`.",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    class ConfirmRemoveView(discord.ui.View):
        def __init__(self, cog, callback_yes, warn_number, removed_log, warn_logs, user, timeout=60):
            super().__init__(timeout=timeout)
            self.cog = cog
            self.callback_yes = callback_yes
            self.warn_number = warn_number
            self.removed_log = copy.deepcopy(removed_log)
            self.warn_logs = warn_logs
            self.user = user

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
        async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                removed_content, remaining_warns = await self.callback_yes(interaction)

                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="Warnings Removed",
                        description=(
                            f"`{removed_content}` and all later warnings were removed.\n\n"
                            f"{self.user.mention} now has `{remaining_warns}` warning(s)."
                        ),
                        color=discord.Color.green()
                    ),
                    ephemeral=False
                )

            except Exception as e:
                print("Failed to handle Yes button:", e)
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("An error occurred while removing warnings.", ephemeral=True)
                    else:
                        await interaction.followup.send("An error occurred while removing warnings.", ephemeral=True)
                except:
                    pass

        @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
        async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)

            try:
                removed_content = self.removed_log.get("content", "*unknown warning*")
                embed = discord.Embed(
                    title="Dismissed Removing Warns Below",
                    description=f"`{removed_content}`\n\n{self.user.mention} now has `{len(self.warn_logs)}` warnings.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                print("Failed to send no-confirmation message:", e)

    @app_commands.command(name="unwarn", description="Remove a warning from a member")
    @app_commands.describe(user="The user to unwarn", warn_number="Which warning number to remove")
    async def unwarn(self, interaction: discord.Interaction, user: discord.User, warn_number: int):
        mod_role_ids = [1367831532240371722]
        if not any(role.id in mod_role_ids for role in interaction.user.roles):
            print(f"[DENY] {interaction.user} is not a moderator.")
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        try:
            print("[DEBUG] Deferring interaction...")
            await asyncio.wait_for(interaction.response.defer(ephemeral=True), timeout=5)
            print("[DEBUG] Interaction deferred.")
        except asyncio.TimeoutError:
            print("[WARN] Deferring interaction timed out.")

        user_id = str(user.id)
        logs = self.mod_logs.get(user_id, [])
        warn_logs = [log for log in logs if isinstance(log, dict) and log.get("type") == "warn"]

        print(f"[INFO] Found {len(warn_logs)} warn entries for user {user_id}")

        if not warn_logs or warn_number < 1 or warn_number > len(warn_logs):
            embed = discord.Embed(
                title="Invalid Warning Number",
                description="The provided warning number is out of range.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        print(f"[INFO] Removing Warn {warn_number} for user {user_id}")
        removed_log = warn_logs.pop(warn_number - 1)
        logs.remove(removed_log)

        warn_logs = [log for log in logs if isinstance(log, dict) and log.get("type") == "warn"]
        for i, log_entry in enumerate(warn_logs):
            new_number = i + 1

            content = log_entry.get("content", "")
            log_entry["content"] = f"Warn {new_number}:{content.split(':', 1)[-1].strip()}"

            try:
                parts = log_entry["log"].split(":", 1)
                if len(parts) == 2:
                    log_entry["log"] = f"Warn {new_number}:{parts[1].strip()}"
            except Exception as e:
                print(f"[ERROR] Failed to reindex log: {e}")
            
            self.save_logs()
            print("[INFO] Logs saved.")

        later_warns = [
            log for log in warn_logs[warn_number - 1:]
            if not log.get("content", "").lower().startswith("timed out")
        ]

        if not later_warns:
            embed = discord.Embed(
                title="Warning Removed",
                description=f"`{removed_log['content']}`\n\n{user.mention} now has `{len(warn_logs)}` warnings.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        print("[INFO] Additional warns found after the removed one. Prompting user for removal confirmation...")

        warn_number_copy = warn_number
        removed_log_copy = removed_log
        user_copy = user

        async def on_confirm(interaction2: discord.Interaction) -> tuple[str, int]:
            try:
                print(f"[INFO] Removing all later warn entries starting from Warn {warn_number_copy}")

                self.mod_logs[str(user_copy.id)][:] = self.mod_logs[str(user_copy.id)][:warn_number_copy - 1]
                warn_logs = self.mod_logs[str(user_copy.id)]

                for i, warn in enumerate(warn_logs):
                    try:
                        new_number = i + 1
                        timestamp = warn.get("timestamp", "unknown time")
                        moderator = "Unknown"
                        reason = "No reason provided"
                        duration = ""

                        if "Warned by" in warn["log"]:
                            try:
                                split_log = warn["log"].split("Warned by", 1)[1]
                                moderator, rest = split_log.split(" for:", 1)
                                reason, time_info = rest.split(" on ", 1)
                                duration = f"on {time_info.strip()}"
                            except Exception as e:
                                print(f"[WARN] Failed to parse original log for reformatting: {e}")

                        warn["log"] = f"Warn {new_number}: Warned by {moderator.strip()} for: {reason.strip()} on {timestamp} {duration}".strip()
                        warn["content"] = f"Warn {new_number}:"
                    except Exception as e:
                        print(f"[ERROR] Failed to reindex warn {i}: {e}")

                self.save_logs()

                return (removed_log_copy["content"], len(warn_logs))

            except Exception as e:
                print("[ERROR] on_confirm exception:", e)
                raise
                await interaction.response.send_message("An error occurred while removing later warns.", ephemeral=True)

        view = self.ConfirmRemoveView(
            cog=self,
            callback_yes=on_confirm,
            warn_number=warn_number,
            removed_log=removed_log,
            warn_logs=warn_logs,
            user=user
        )


        embed = discord.Embed(
            title="⚠️ Alert",
            description=f"Would you like to remove the warns below Warn {warn_number}?",
            color=discord.Color.orange()
        )

        try:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            print("[INFO] Prompt sent.")
        except Exception as e:
            print("[ERROR] Failed to send confirmation prompt:", e)

        print("[INFO] Confirmation prompt sent.")

    @app_commands.command(name="unban", description="Unban a user by their user ID")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for the unban")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        mod_role_ids = [1367831532240371722]
        if not any(role.id in mod_role_ids for role in interaction.user.roles):
            embed = discord.Embed(
                title="Access Denied",
                description="You do not have permission to use this command.",
                color=discord.Color.red()
            )
            print(f"[DENY] {interaction.user} is not a moderator.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user_id_int = int(user_id)
            user = await self.bot.fetch_user(user_id_int)

            bans = [ban async for ban in interaction.guild.bans()]
            banned_user = next((ban for ban in bans if ban.user.id == user_id_int), None)

            if not banned_user:
                embed = discord.Embed(
                    title="User Not Found",
                    description="User is not banned.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.guild.unban(user, reason=reason)

            embed = discord.Embed(
                title="User Unbanned",
                description=f"{user.mention} (`{user.id}) has been unbanned.\n**Reason:** {reason}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)

        except ValueError:
            embed = discord.Embed(
                title="Invalid Format",
                description="Invalid user ID format.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.NotFound:
            embed = discord.Embed(
                title="User Not Found",
                description="User not found/User is already unbanned.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            embed = discord.Embed(
                title="Invalid Permissions [BOT]",
                description="Bot doesn't have permissions to unban users. **Ping/DM <@945608534010241024> if you see this message.**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="Internal Error",
                description=f"An unexpected error occurred.\n**`{e}`**",
                color=discord.Color.red()
            )
            print(f"[ERROR] Failed to unban user {user_id}: {e}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModLogsSystem(bot))
