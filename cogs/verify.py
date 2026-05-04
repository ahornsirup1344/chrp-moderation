import discord
from discord.ext import commands
import aiohttp
import asyncio
import random
import time
import os
import json
from settings.verify_codes import VERIFICATION_WORDS
from supabase import create_client
from datetime import datetime


#Supabase setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _load_json(self):
    try:
        with open("all.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"verify_panel_id": []}

def _save_json(self, data):
    try:
        with open("all.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Fehler beim Schreiben in all.json:", e)

def _env_list(key: str):
    value = os.environ.get(key, "")
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class VerifyCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_key = os.environ.get("ERLC_SERVER_KEY")
        self.verification_channel_id = int(os.environ.get("VERIFICATION_CHANNEL_ID", "0") or 0)
        self.add_role_ids = _env_list("ADD_ROLE_IDS")
        self.remove_role_ids = _env_list("REMOVE_ROLE_IDS")
        self.code_ttl = int(os.environ.get("CODE_TTL_SECONDS", "600"))
        self.verify_log_channel_id = int(os.environ.get("VERIFY_LOG_CHANNEL_ID", "0") or 0)

        self.pending = {}
        self.lock = asyncio.Lock()

        self.http = aiohttp.ClientSession()
        self._cleanup_task = self.bot.loop.create_task(self._cleanup_loop())
        self.bot.loop.create_task(self._initialize_panel())

        # ---------------- JSON Funktionen ----------------
    def _load_json(self):
        try:
            with open("all.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"verify_panel_id": []}

    def _save_json(self, data):
        try:
            with open("all.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Fehler beim Schreiben in all.json:", e)

    async def cog_unload(self):
        try:
            self._cleanup_task.cancel()
        except Exception:
            pass
        await self.http.close()

    async def _cleanup_loop(self):
        try:
            while True:
                await asyncio.sleep(30)
                now = time.time()
                async with self.lock:
                    to_del = [k for k, v in self.pending.items() if v.get("expires", 0) < now]
                    for k in to_del:
                        del self.pending[k]
        except asyncio.CancelledError:
            return

    async def _initialize_panel(self):
        await self.bot.wait_until_ready()  # sicherstellen, dass alle Guilds geladen sind
        data = self._load_json()
        if not data.get("verify_panel_id"):
            return  # kein Panel gespeichert, nichts zu tun

        panel_id = data["verify_panel_id"][0]
        # Wir gehen durch alle Guilds und Channels, bis wir die Nachricht finden
        for guild in self.bot.guilds:
            try:
                for channel in guild.text_channels:
                    try:
                        msg = await channel.fetch_message(panel_id)
                        if msg:
                            embed = discord.Embed(
                                title="🎫 Server-Verifizierung",
                                description="Klicke **Verifizieren** um deinen Roblox-Namen einzugeben oder **Code eingeben** wenn du bereits einen Code erhalten hast. \n\n **Bitte beachte:** \n`Mit dem Verifizieren akzeptierst du automatisch unser Regelwerk`.",
                                color=0x2f3136
                            )
                            embed.set_footer(text="Nur wer auf unserem ER:LC Privatserver ist, kann sich verifizieren.")
                            view = VerifyPanelView(self)
                            await msg.edit(embed=embed, view=view)
                            print(f"Verify-Panel in {guild.name}/{channel.name} aktualisiert.")
                            return
                    except discord.NotFound:
                        continue
            except Exception as e:
                print(f"Fehler beim Aktualisieren des Verify Panels in {guild.name}: {e}")

    # ---------------- ER:LC API Abfrage ----------------
    async def _is_user_in_server(self, roblox_username: str) -> tuple[bool, str]:

        if not self.server_key:
            raise RuntimeError("ERLC_SERVER_KEY ist nicht konfiguriert.")

        url = "https://api.policeroleplay.community/v1/server/players"
        headers = {"server-key": self.server_key}
        try:
            async with self.http.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 403:
                    raise RuntimeError("ERLC Server-Key ungültig (403).")
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"ERLC API Fehler {resp.status}: {text}")
                data = await resp.json()
                # data: list von Objekten mit "Player": "Name:Id"
                for entry in data:
                    player_field = entry.get("Player") or entry.get("player") or ""
                    parts = str(player_field).split(":")
                    name = parts[0] if parts else ""
                    player_id = parts[1] if len(parts) > 1 else "unbekannt"
                    if name.lower() == roblox_username.lower():
                        return True, player_id
                # Wenn kein Spieler gefunden wurde, geben wir ein konsistentes Tuple zurück
                return False, "unbekannt"
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout beim Kontaktieren der ER:LC API.")
        except Exception:
            # Weiterwerfen, damit der Aufrufer die Fehlerbehandlung erledigen kann
            raise

    # ---------------- Roblox PM senden ----------------
    async def _send_roblox_pm(self, roblox_username: str, message: str):
        if not self.server_key:
            raise RuntimeError("ERLC_SERVER_KEY nicht konfiguriert")

        url = "https://api.policeroleplay.community/v1/server/command"
        headers = {"server-key": self.server_key}
        payload = {
            "command": f":pm {roblox_username} {message}"
        }

        async with self.http.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Fehler beim Senden der PM: {resp.status} {text}")

    # ---------------- Supabase ----------------
    async def _append_to_db(self, member: discord.Member, roblox_username: str, roblox_id: str):
        """Speichert einen neuen Verifizierungs-Eintrag in Supabase."""
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: supabase.table("verify").insert({
                    "discord_id": member.id,
                    "discord_name": str(member),
                    "roblox_id": str(roblox_id),
                    "roblox_name": str(roblox_username),
                    "date": datetime.utcnow().isoformat()
                }).execute()
            )
        except Exception as e:
            print(f"[Supabase] Fehler beim Einfügen: {e}")

    async def _check_duplicate_in_db(self, member: discord.Member, roblox_username: str) -> bool:
        """Prüft, ob Discord ID oder Roblox Username schon in Supabase existieren."""
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: supabase.table("verify")
                .select("*")
                .or_(f"discord_id.eq.{member.id},roblox_name.eq.{roblox_username}")
                .execute()
            )
            if result.data and len(result.data) > 0:
                return True
            return False
        except Exception as e:
            print(f"[Supabase] Fehler bei Dublettenprüfung: {e}")
            return False

    async def _delete_from_db(self, member: discord.Member) -> bool:
        """Löscht den Eintrag aus Supabase anhand der Discord-ID."""
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: supabase.table("verify").delete().eq("discord_id", member.id).execute()
            )
            return True
        except Exception as e:
            print(f"[Supabase] Fehler beim Löschen: {e}")
            return False

    async def _update_discord_name_in_db(self, user: discord.User) -> bool:
        """Aktualisiert den Discord-Namen in Supabase anhand der Discord-ID."""
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: supabase.table("verify").update({"discord_name": str(user)}).eq("discord_id", user.id).execute()
            )
            return True
        except Exception as e:
            print(f"[Supabase] Fehler beim Aktualisieren des Discord-Namens: {e}")
            return False

    # ---------------- Command: !send_verifypanel (Admin only) ----------------
    @commands.command(name="send_verifypanel")
    @commands.has_permissions(administrator=True)
    async def send_verifypanel(self, ctx: commands.Context):
        """Postet das Verifikations-Embed + Buttons (nur Admins)."""
        post_channel = ctx.channel
        if self.verification_channel_id:
            ch = ctx.guild.get_channel(self.verification_channel_id)
            if ch:
                post_channel = ch

        embed = discord.Embed(
            title="🎫 Server-Verifizierung",
            description="Klicke **Verifizieren** um deinen Roblox-Namen einzugeben oder **Code eingeben** wenn du bereits einen Code erhalten hast. \n\n **Bitte beachte:** \n`Mit dem Verifizieren akzeptierst du automatisch unser Regelwerk`.",
            color=0x2f3136
        )
        embed.set_footer(text="Nur wer auf unserem ER:LC Privatserver ist, kann sich verifizieren.")
        view = VerifyPanelView(self)

        # ---------------- Speichern / Überprüfen ----------------
        data = self._load_json()
        if not data.get("verify_panel_id"):
            msg = await post_channel.send(embed=embed, view=view)
            data["verify_panel_id"] = [msg.id]  # Message-ID speichern
            self._save_json(data)
            # Statt Reaktion -> Command-Nachricht löschen
            try:
                await ctx.message.delete()
            except Exception:
                pass
            return
        else:
            # Wenn ID schon existiert -> Nachricht editieren
            try:
                panel_id = data["verify_panel_id"][0]
                msg = await post_channel.fetch_message(panel_id)
                await msg.edit(embed=embed, view=view)
                # Command-Nachricht löschen
                try:
                    await ctx.message.delete()
                except Exception:
                    pass
            except Exception as e:
                await ctx.send(f"Fehler beim Bearbeiten des Verify Panels: {e}")

    # ---------------- Handling der Modal-Submits ----------------
    async def handle_username_submission(self, interaction: discord.Interaction, roblox_username: str):
        """Wird aufgerufen, wenn ein User seinen Roblox-User über das Modal eingibt."""
        await interaction.response.defer(ephemeral=True)
        try:
            in_server, roblox_id = await self._is_user_in_server(roblox_username)
        except Exception as e:
            await interaction.followup.send(f"Fehler beim Abfragen der ER:LC API: {e}", ephemeral=True)
            return

        if not in_server:
            await interaction.followup.send(
                "Dein Roblox-Account wurde nicht auf unserem privaten ER:LC Server gefunden. Bitte trete zuerst dem Server bei und versuche es erneut.",
                ephemeral=True
            )
            return

        code = random.choice(VERIFICATION_WORDS)
        member = interaction.user
        try:
            await self._send_roblox_pm(
                roblox_username,
                f"{code}"
            )
        except Exception as e:
            await interaction.followup.send(f"Fehler beim Senden des Codes auf dem Roblox-Server: {e}", ephemeral=True)
            return

        expires = time.time() + self.code_ttl
        async with self.lock:
            self.pending[interaction.user.id] = {
                "code": code,
                "roblox": roblox_username,
                "roblox_id": roblox_id,
                "expires": expires
            }
        await interaction.followup.send("Der Code wurde per Direktnachricht gesendet. Gib ihn im Panel unter 'Code eingeben' ein.", ephemeral=True)

    async def handle_code_submission(self, interaction: discord.Interaction, code_input: str):
        """Wird aufgerufen, wenn der User seinen 4-stelligen Code eingibt."""
        await interaction.response.defer(ephemeral=True)
        async with self.lock:
            entry = self.pending.get(interaction.user.id)
        if not entry:
            await interaction.followup.send(
                "Kein aktiver Verifizierungsversuch gefunden. Bitte klicke zuerst auf 'Verifizieren'.", ephemeral=True)
            return
        if time.time() > entry.get("expires", 0):
            async with self.lock:
                if interaction.user.id in self.pending:
                    del self.pending[interaction.user.id]
            await interaction.followup.send("Der Code ist abgelaufen. Bitte starte die Verifizierung neu.",
                                            ephemeral=True)
            return
        if str(code_input).strip() != str(entry.get("code")):
            await interaction.followup.send("Falscher Code. Bitte überprüfe die Direktnachricht.", ephemeral=True)
            return

        guild = interaction.guild
        try:
            member = guild.get_member(interaction.user.id) or await guild.fetch_member(interaction.user.id)

            # --- DUBLETTENPRÜFUNG ---
            is_duplicate = await self._check_duplicate_in_db(member, entry.get("roblox"))
            if is_duplicate:
                await interaction.followup.send(
                    "Dieser Discord-Account oder Roblox-Benutzer wurde bereits verifiziert.",
                    ephemeral=True
                )
                return

            # entfernen
            for r in self.remove_role_ids:
                try:
                    rid = int(r)
                except Exception:
                    continue
                role = guild.get_role(rid)
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="ER:LC verification")
                    except Exception as e:
                        print("Fehler remove_roles:", e)

            # hinzufügen
            for r in self.add_role_ids:
                try:
                    rid = int(r)
                except Exception:
                    continue
                role = guild.get_role(rid)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="ER:LC verification")
                    except Exception as e:
                        print("Fehler add_roles:", e)

            await self._append_to_db(member, entry.get("roblox"), entry.get("roblox_id"))

            async with self.lock:
                if interaction.user.id in self.pending:
                    del self.pending[interaction.user.id]

            await interaction.followup.send(f"Verifikation erfolgreich — **{entry.get('roblox')}** wurde verknüpft.",
                                            ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Fehler bei der Verifikation / Rollen-Zuweisung: {e}", ephemeral=True)
            return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Wenn ein Mitglied den Server verlässt, lösche seinen Eintrag aus der Google Sheet und logge es."""
        try:
            deleted = await self._delete_from_db(member)

            embed = discord.Embed(
                title="👋 Mitglied hat den Server verlassen",
                description=f"{member.mention} (`{member}` / `{member.id}`)",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            if deleted:
                embed.add_field(name="Google Sheets", value="✅ Eintrag erfolgreich gelöscht", inline=False)
            else:
                embed.add_field(name="Google Sheets", value="⚠️ Kein Eintrag gefunden oder Fehler", inline=False)

            if self.verify_log_channel_id:
                log_channel = member.guild.get_channel(self.verify_log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Fehler im on_member_remove Event: {e}")

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Aktualisiert den Discord-Namen in der Google Sheet, wenn der User seinen Namen ändert."""
        if before.name == after.name:
            return  # Name hat sich nicht geändert

        try:
            updated = await self._update_discord_name_in_db(after)

            if updated and self.verify_log_channel_id:
                log_channel = None
                for guild in after.mutual_guilds:
                    ch = guild.get_channel(self.verify_log_channel_id)
                    if ch:
                        log_channel = ch
                        break
                if log_channel:
                    embed = discord.Embed(
                        title="✏️ Discord-Name aktualisiert",
                        description=f"{before.name} → {after.name}",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Fehler im on_user_update Event: {e}")

# ---------------- UI: View + Modals ----------------
class VerifyPanelView(discord.ui.View):
    def __init__(self, cog: VerifyCog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.primary, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UsernameModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Code eingeben", style=discord.ButtonStyle.secondary, custom_id="code_button")
    async def code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CodeModal(self.cog)
        await interaction.response.send_modal(modal)

class UsernameModal(discord.ui.Modal, title="Roblox Benutzername"):
    def __init__(self, cog: VerifyCog):
        super().__init__()
        self.cog = cog
        self.username = discord.ui.TextInput(label="Roblox Benutzername", placeholder="maxmustermann12", max_length=50, required=True)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.handle_username_submission(interaction, self.username.value.strip())

class CodeModal(discord.ui.Modal, title="Verifizierungs-Code"):
    def __init__(self, cog: VerifyCog):
        super().__init__()
        self.cog = cog
        self.code = discord.ui.TextInput(label="5-stelliger Code", placeholder="JsdKw", min_length=5, max_length=5, required=True)
        self.add_item(self.code)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.handle_code_submission(interaction, self.code.value.strip())

async def setup(bot: commands.Bot):
    await bot.add_cog(VerifyCog(bot))