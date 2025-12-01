import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta

class UserCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="usercard", description="Show user card")
    @app_commands.describe(user="User to get info about")
    async def usercard(self, interaction: discord.Interaction, user: str):
        guild = interaction.guild
        target_user = None

        if user.isdigit():
            try:
                target_user = await self.bot.fetch_user(int(user))
            except:
                pass
        elif user.startswith("<@") and user.endswith(">"):
            try:
                user_id = int(user.strip("<@!>"))
                target_user = await self.bot.fetch_user(user_id)
            except:
                pass
        elif "#" in user:
            try:
                name, discrim = user.split("#")
                for m in guild.members:
                    if m.name == name and m.discriminator == discrim:
                        target_user = m
                        break
            except:
                pass

        if not target_user:
            await interaction.response.send_message("User not found. Please use a mention, tag, or valid ID.", ephemeral=True)
            return

        member = guild.get_member(target_user.id)

        mod_role_ids = [1367831532240371722]
        invoker = interaction.user
        print("[DEBUG, usercards2] Passing through first isinstance block...")
        if isinstance(invoker, discord.Member):
            is_mod = any(role.id in mod_role_ids for role in interaction.user.roles)
            print(f"Roles: {[role.id for role in interaction.user.roles]}")
            print(f"is_mod: {is_mod}")
            print("[DEBUG, usercards2] Passed through first isinstance block successfully.")

        else:
            is_mod = False

        print("[DEBUG, usercards2] Passing through defer line...")
        print(f"[DEBUG, usercards2] is_mod value = {is_mod}")
        try:
            await interaction.response.defer(ephemeral=is_mod)
        except Exception as e:
            print(f"[DEBUG, usercards2] An error occured while trying to defer : {e}")
        print("[DEBUG, usercards2] Passed through defer line successfully.")

        embed = discord.Embed(title=f"{target_user}'s Usercard", color=discord.Color.blue())
        embed.set_thumbnail(url=target_user.display_avatar.url)

        embed.add_field(name="User", value=f"{target_user.mention}", inline=True)
        if member:
            embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        else:
            embed.add_field(name="Joined Server", value="Not in server", inline=True)
        embed.add_field(name="Account Created", value=target_user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)

        print("[DEBUG, usercards2] Passing through is_mod block...")
        if is_mod:
            modlogs_cog = self.bot.get_cog("ModLogsSystem")
            if modlogs_cog:
                modlogs_cog.clean_expired_warns_for_user(str(target_user.id))

                raw_logs = modlogs_cog.mod_logs.get(str(target_user.id), [])
                mod_logs = []

                now = datetime.utcnow()

                for log in raw_logs:
                    if isinstance(log, str):
                        mod_logs.append(log)
                        continue
                    
                    if isinstance(log, dict) and log.get("type") == "warn":
                        log_str = log.get("log", "Warn")
                        expires_str = log.get("expires_at")
                        issued_str = log.get("timestamp")

                        if issued_str:
                            try:
                                issued_at = datetime.strptime(issued_str, "%Y-%m-%d %H:%M:%S")
                                issued_ts = int(issued_at.timestamp())
                                issued_display = f"<t:{issued_ts}:f> • <t:{issued_ts}:R>"
                            except:
                                issued_display = issued_str
                        else:
                            issued_display = "Unknown"

                        if expires_str:
                            try:
                                expires_at = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
                                seconds = int((expires_at - now).total_seconds())
                                if seconds <= 0:
                                    duration_str = "Expired"
                                else:
                                    ts = int(expires_at.timestamp())
                                    duration_str = f"expires <t:{ts}:R> (<t:{ts}:f>)"
                            except:
                                duration_str = "Unknown"
                        else:
                            duration_str = "Permanent"

                        mod_logs.append(f"{log_str} — *{duration_str}*\nIssued at: {issued_display}")
                        print("Passed through is_mod block successfully.")

                embed.add_field(
                    name="Mod Logs",
                    value="\n".join(mod_logs) if mod_logs else "No mod logs found.",
                    inline=False
                )
                embed.color = discord.Color.blurple()
        print("[DEBUG, usercards2] Sending usercard embed...")
        try:
            await interaction.followup.send(embed=embed)
            print("Sent usercard successfully.")
        except Exception as e:
            print("[DEBUG, usercards2] Error sending usercard:", e)
            await interaction.followup.send(
                "An internal error happened while running this command.",
                ephemeral=True
            )



async def setup(bot):
    await bot.add_cog(UserCard(bot))
