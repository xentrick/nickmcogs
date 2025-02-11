from redbot.core import Config
import asyncio
import discord

import logging

log = logging.getLogger("red.nickmcogs.Leveler.userprofile")


class UserProfile:
    def __init__(self):
        self.data = Config.get_conf(self, identifier=1099710897114110101)
        default_guild = {
            "wlchannels": [],
            "blchannels": [],
            "defaultrole": None,
            "defaultbg": None,
            "roles": {},
            "database": [],
            "autoregister": False,
            "cooldown": 60.0,
            "whitelist": True,
            "blacklist": False,
            "lvlup_announce": False,
        }
        default_member = {
            "exp": 0,
            "level": 1,
            "today": 0,
            "lastmessage": 0.0,
            "background": None,
            "description": "",
        }
        self.data.register_member(**default_member)
        self.data.register_guild(**default_guild)

    async def _set_guild_background(self, guild: discord.Guild, bg: str):
        await self.data.guild(guild).defaultbg.set(bg)

    async def _give_exp(self, member: discord.Member, exp: int):
        current = await self.data.member(member).exp()
        await self.data.member(member).exp.set(current + exp)
        await self._check_exp(member)

    async def _set_exp(self, member: discord.Member, exp: int):
        await self.data.member(member).exp.set(exp)
        await self._check_exp(member)

    async def _set_level(self, member: discord.Member, level):
        await self.data.member(member).level.set(level)

    async def _is_registered(self, member: discord.Member):
        async with self.data.guild(member.guild).database() as db:
            return member.id in db

    async def _register_user(self, member: discord.Member):
        data = await self.data.guild(member.guild).database()
        if data is None:
            await self.data.guild(member.guild).database.set([])
        async with self.data.guild(member.guild).database() as db:
            db.append(member.id)
        await self.data.member(member).exp.set(0)

    async def _set_user_lastmessage(self, member: discord.Member, lastmessage: float):
        await self.data.member(member).lastmessage.set(lastmessage)

    async def _get_user_lastmessage(self, member: discord.Member):
        return await self.data.member(member).lastmessage()

    async def _downgrade_level(self, member: discord.Member):
        lvl = await self.data.member(member).level()
        pastlvl = 5 * ((lvl - 2) ** 2) + (50 * (lvl - 2)) + 100
        xp = await self.data.member(member).exp()
        while xp < pastlvl and not lvl <= 1:
            lvl -= 1
            pastlvl = 5 * ((lvl - 1) ** 2) + (50 * (lvl - 1)) + 100
        await self.data.member(member).level.set(lvl)

    async def _check_exp(self, member: discord.Member):
        lvl = await self.data.member(member).level()
        lvlup = 5 * ((lvl - 1) ** 2) + (50 * (lvl - 1)) + 100
        xp = await self.data.member(member).exp()
        if xp >= lvlup:
            await self.data.member(member).level.set(lvl + 1)
            lvl += 1
            lvlup = 5 * ((lvl - 1) ** 2) + (50 * (lvl - 1)) + 100
            if xp >= lvlup:
                await self._check_exp(member)
        elif xp < lvlup and lvl > 1:
            await self._downgrade_level(member)

    async def _check_role_member(self, member: discord.Member):
        roles = await self.data.guild(member.guild).roles()
        lvl = await self.data.member(member).level()
        log.debug(f"lvl: {lvl}")
        log.debug(f"roles: {roles}")
        for k, v in roles.items():
            if lvl == int(k):
                rl = discord.utils.get(member.guild.roles, id=v)
                if rl in member.roles:
                    return True
                else:
                    to_remove = []
                    for r in roles.values():
                        if r == v:
                            continue
                        grole = member.guild.get_role(r)
                        if grole and grole in member.roles:
                            to_remove.append(grole)
                    # to_remove = [member.guild.get_role(r) for r in roles.values() if r != v]
                    if to_remove:
                        log.debug(f"Removing old leveler roles: {to_remove}")
                        await member.remove_roles(*to_remove, reason="User leveled up")
                    if rl:
                        log.debug(f"Adding leveler role: {rl.name}")
                        await member.add_roles(rl, reason="User leveled up")
                    return True
            else:
                pass
        return False

    async def _add_guild_role(self, guild: discord.Guild, level: int, roleid: int):
        role = discord.utils.get(guild.roles, id=roleid)
        if role is None:
            return False
        rl = await self.data.guild(guild).roles()
        if isinstance(rl, list):
            rl = {}
        rl.update({str(level): roleid})
        await self.data.guild(guild).roles.set(rl)

    async def _remove_guild_role(self, guild: discord.Guild, role: discord.Role):
        rolelist = await self.data.guild(guild).roles()
        for k, v in rolelist.items():
            if v == role.id:
                del rolelist[k]
                await self.data.guild(guild).roles.set(rolelist)
                return

    async def _remove_guild_level(self, guild: discord.Guild, lvl: str):
        rolelist = await self.data.guild(guild).roles()
        for k in rolelist.keys():
            if k == lvl:
                del rolelist[k]
                await self.data.guild(guild).roles.set(rolelist)
                return

    async def _get_guild_roles(self, guild: discord.Guild):
        return await self.data.guild(guild).roles()

    async def _add_guild_channel(self, guild: discord.Guild, channel: discord.TextChannel):
        async with self.data.guild(guild).wlchannels() as chanlist:
            chanlist.append(channel)

    async def _remove_guild_channel(self, guild: discord.Guild, channel: discord.TextChannel):
        async with self.data.guild(guild).wlchannels() as chanlist:
            chanlist.remove(channel)

    async def _get_guild_channels(self, guild: discord.Guild):
        return await self.data.guild(guild).wlchannels()

    async def _add_guild_blacklist(self, guild: discord.Guild, channel: discord.TextChannel):
        async with self.data.guild(guild).blchannels() as chanlist:
            chanlist.append(channel)

    async def _remove_guild_blacklist(self, guild: discord.Guild, channel: discord.TextChannel):
        async with self.data.guild(guild).blchannels() as chanlist:
            chanlist.remove(channel)

    async def _get_guild_blchannels(self, guild: discord.Guild):
        return await self.data.guild(guild).blchannels()

    async def _toggle_whitelist(self, guild: discord.Guild):
        wl = await self.data.guild(guild).whitelist()
        if wl:
            await self.data.guild(guild).whitelist.set(False)
            return False
        else:
            await self.data.guild(guild).whitelist.set(True)
            return True

    async def _toggle_blacklist(self, guild: discord.Guild):
        bl = await self.data.guild(guild).blacklist()
        if bl:
            await self.data.guild(guild).blacklist.set(False)
            return False
        else:
            await self.data.guild(guild).blacklist.set(True)
            return True

    async def _get_exp(self, member: discord.Member):
        return await self.data.member(member).exp()

    async def _get_level(self, member: discord.Member):
        return await self.data.member(member).level()

    async def _get_xp_for_level(self, lvl: int):
        return 5 * ((lvl - 1) ** 2) + (50 * (lvl - 1)) + 100

    async def _get_level_exp(self, member: discord.Member):
        lvl = await self.data.member(member).level()
        return await self._get_xp_for_level(lvl)

    async def _get_today(self, member: discord.Member):
        return await self.data.member(member).today()

    async def _today_addone(self, member: discord.Member):
        await self.data.member(member).today.set(await self._get_today(member) + 1)

    async def _set_auto_register(self, guild: discord.Guild, autoregister: bool):
        await self.data.guild(guild).autoregister.set(autoregister)

    async def _get_auto_register(self, guild: discord.Guild):
        return await self.data.guild(guild).autoregister()

    async def _set_cooldown(self, guild: discord.Guild, cooldown: float):
        await self.data.guild(guild).cooldown.set(cooldown)

    async def _get_cooldown(self, guild: discord.Guild):
        return await self.data.guild(guild).cooldown()

    async def _set_background(self, member: discord.Member, background: str |None=None):
        await self.data.member(member).background.set(background)

    async def _get_background(self, member: discord.Member):
        userbg = await self.data.member(member).background()
        if userbg is None:
            userbg = await self.data.guild(member.guild).defaultbg()
        return userbg

    async def _set_description(self, member: discord.Member, description: str):
        await self.data.member(member).description.set(description)

    async def _get_description(self, member: discord.Member):
        return await self.data.member(member).description()

    async def _get_leaderboard_pos(self, guild: discord.Guild, member: discord.Member):
        datas = await self.data.all_members(guild)
        infos = sorted(datas, key=lambda x: datas[x]["exp"], reverse=True)
        return infos.index(member.id) + 1

    async def _get_leaderboard(self, guild: discord.Guild):
        datas = await self.data.all_members(guild)
        infos = sorted(datas, key=lambda x: datas[x]["exp"], reverse=True)
        res = []
        count = 1
        for i in infos:
            tmp = {}
            tmp["id"] = i
            cur = datas[i]
            tmp["xp"] = cur["exp"]
            tmp["lvl"] = cur["level"]
            tmp["today"] = cur["today"]
            res.append(tmp)
            count += 1
            if count == 10:
                break
        return res
