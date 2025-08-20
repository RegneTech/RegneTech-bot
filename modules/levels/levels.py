import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
import asyncio
import random
from datetime import datetime, timedelta
from database import (
    get_user_level_data, 
    get_user_balance, 
    get_user_rank,
    get_guild_level_config,
    add_user_xp,
    set_user_xp,
    set_user_level,
    get_leaderboard,
    get_weekly_leaderboard,
    get_monthly_leaderboard
)
import math

class LevelsSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_path = "resources/fonts" 
        self.bg_path = "resources/images/perfil"
        
        # Canal para anuncios de level up
        self.level_up_channel_id = 1400106793249538048
        
        # Roles por niveles
        self.level_roles = {
            10: 1400106792196898893,
            20: 1400106792196898894,
            30: 1400106792196898895,
            40: 1400106792226127914,
            50: 1400106792226127915,
            60: 1400106792226127916,
            70: 1400106792226127917,
            80: 1400106792226127918,
            90: 1400106792226127919,
            100: 1400106792226127920,
            110: 1400106792226127921,
            120: 1400106792226127922,
            130: 1400106792226127923,
            140: 1400106792280658061,
            150: 1400106792280658062,
            160: 1400106792280658063,
            170: 1400106792280658064,
            180: 1400106792280658065,
            190: 1400106792280658066,
            200: 1400106792280658067
        }
        
        # Multiplicadores de XP por rol
        self.xp_multipliers = {}  # {role_id: {'multiplier': float, 'expires': datetime}}
        
        # Usuarios activos para dar XP
        self.active_users = set()
        
        # Iniciar tarea de XP automático
        self.auto_xp_task.start()
        
        # Tabla de XP por niveles (ÚNICA FUENTE DE VERDAD)
        self.xp_table = {
            1: 1000, 2: 1050, 3: 1100, 4: 1150, 5: 1200, 6: 1250, 7: 1300, 8: 1355,
            9: 1405, 10: 1455, 11: 1505, 12: 1555, 13: 1605, 14: 1660, 15: 1710,
            16: 1760, 17: 1810, 18: 1860, 19: 1910, 20: 1960, 21: 2010, 22: 2060,
            23: 2110, 24: 2160, 25: 2210, 26: 2260, 27: 2310, 28: 2360, 29: 2410,
            30: 2460, 31: 2510, 32: 2560, 33: 2610, 34: 2660, 35: 2710, 36: 2760,
            37: 2810, 38: 2860, 39: 2910, 40: 2960, 41: 3010, 42: 3060, 43: 3110,
            44: 3160, 45: 3210, 46: 3275, 47: 3325, 48: 3375, 49: 3425, 50: 3475,
            51: 3525, 52: 3575, 53: 3625, 54: 3675, 55: 3725, 56: 3775, 57: 3825,
            58: 3875, 59: 3925, 60: 3975, 61: 4025, 62: 4075, 63: 4125, 64: 4175,
            65: 4225, 66: 4275, 67: 4325, 68: 4375, 69: 4425, 70: 4475, 71: 4525,
            72: 4575, 73: 4625, 74: 4675, 75: 4725, 76: 4775, 77: 4825, 78: 4875,
            79: 4925, 80: 4975, 81: 5025, 82: 5075, 83: 5125, 84: 5175, 85: 5225,
            86: 5275, 87: 5325, 88: 5375, 89: 5425, 90: 5475, 91: 5525, 92: 5575,
            93: 5625, 94: 5675, 95: 5725, 96: 5775, 97: 5825, 98: 5875, 99: 5925,
            100: 5975, 101: 6025, 102: 6075, 103: 6125, 104: 6175, 105: 6225,
            106: 6275, 107: 6325, 108: 6375, 109: 6425, 110: 6475, 111: 6525,
            112: 6575, 113: 6625, 114: 6675, 115: 6725, 116: 6775, 117: 6825,
            118: 6875, 119: 6925, 120: 6975, 121: 7025, 122: 7075, 123: 7125,
            124: 7175, 125: 7225, 126: 7275, 127: 7325, 128: 7375, 129: 7425,
            130: 7475, 131: 7525, 132: 7575, 133: 7625, 134: 7675, 135: 7725,
            136: 7775, 137: 7825, 138: 7875, 139: 7925, 140: 7975, 141: 8025,
            142: 8075, 143: 8125, 144: 8175, 145: 8225, 146: 8275, 147: 8325,
            148: 8375, 149: 8425, 150: 8475, 151: 8525, 152: 8575, 153: 8625,
            154: 8675, 155: 8725, 156: 8775, 157: 8825, 158: 8875, 159: 8925,
            160: 8975, 161: 9025, 162: 9075, 163: 9125, 164: 9175, 165: 9225,
            166: 9275, 167: 9325, 168: 9375, 169: 9425, 170: 9475, 171: 9525,
            172: 9575, 173: 9625, 174: 9675, 175: 9725, 176: 9775, 177: 9825,
            178: 9875, 179: 9925, 180: 9975, 181: 10025, 182: 10075, 183: 10125,
            184: 10175, 185: 10225, 186: 10275, 187: 10325, 188: 10375, 189: 10425,
            190: 10475, 191: 10525, 192: 10575, 193: 10625, 194: 10675, 195: 10725,
            196: 10775, 197: 10825, 198: 10875, 199: 10925, 200: 11675
        }
        
        # XP acumulada por nivel
        self.cumulative_xp = {}
        self._calculate_cumulative_xp()
    
    def _calculate_cumulative_xp(self):
        """Calcula la XP acumulada para cada nivel"""
        total = 0
        for level in range(1, 201):
            if level > 1:
                total += self.xp_table.get(level - 1, 0)
            self.cumulative_xp[level] = total
    
    def cog_unload(self):
        """Detiene las tareas al descargar el cog"""
        self.auto_xp_task.cancel()
    
    # ================== EVENTOS ==================
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Registra usuarios activos para dar XP"""
        if message.author.bot:
            return
        
        # Agregar usuario a la lista de activos
        self.active_users.add((message.author.id, message.guild.id))
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Registra usuarios activos en canales de voz"""
        if member.bot:
            return
        
        # Si se unió a un canal de voz, agregarlo a activos
        if after.channel and not before.channel:
            self.active_users.add((member.id, member.guild.id))
    
    # ================== TAREAS AUTOMÁTICAS ==================
    
    @tasks.loop(minutes=1)
    async def auto_xp_task(self):
        """Tarea que da XP automáticamente cada minuto"""
        if not self.active_users:
            return
        
        # Copiar y limpiar la lista de usuarios activos
        users_to_reward = list(self.active_users)
        self.active_users.clear()
        
        for user_id, guild_id in users_to_reward:
            try:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                
                member = guild.get_member(user_id)
                if not member or member.bot:
                    continue
                
                # Generar XP aleatoria (5-50 en múltiplos de 5)
                base_xp = random.choice([5, 10, 15, 20, 25, 30, 35, 40, 45, 50])
                
                # Aplicar multiplicadores de rol
                multiplier = 1.0
                for role in member.roles:
                    if role.id in self.xp_multipliers:
                        mult_data = self.xp_multipliers[role.id]
                        if datetime.now() < mult_data['expires']:
                            multiplier = max(multiplier, mult_data['multiplier'])
                        else:
                            # Eliminar multiplicador expirado
                            del self.xp_multipliers[role.id]
                
                final_xp = int(base_xp * multiplier)
                
                # Agregar XP y verificar level up
                await self.add_xp_and_check_levelup(member, final_xp)
                
            except Exception as e:
                print(f"Error dando XP automática a {user_id}: {e}")
    
    @auto_xp_task.before_loop
    async def before_auto_xp_task(self):
        """Espera a que el bot esté listo"""
        await self.bot.wait_until_ready()
    
    # ================== FUNCIONES AUXILIARES (CORREGIDAS) ==================
    
    def get_level_from_total_xp(self, total_xp: int) -> tuple:
        """ÚNICA función para calcular nivel desde XP total - USA LA TABLA FIJA"""
        current_level = 1
        
        # Encontrar el nivel actual basado en XP acumulada
        for level in range(1, 201):
            if total_xp < self.cumulative_xp.get(level + 1, float('inf')):
                current_level = level
                break
        
        # XP actual en el nivel
        current_level_start_xp = self.cumulative_xp.get(current_level, 0)
        current_xp_in_level = total_xp - current_level_start_xp
        
        # XP necesaria para el siguiente nivel
        next_level_xp = self.xp_table.get(current_level, 0)
        
        return current_level, current_xp_in_level, next_level_xp
    
    def get_total_xp_for_level(self, level: int) -> int:
        """Obtiene la XP total necesaria para alcanzar un nivel"""
        return self.cumulative_xp.get(level, 0)
    
    async def add_xp_and_check_levelup(self, member: discord.Member, xp_amount: int):
        """Agrega XP a un usuario y verifica si subió de nivel"""
        try:
            # Obtener datos actuales del usuario
            user_data = await get_user_level_data(member.id, member.guild.id)
            if not user_data:
                return
            
            old_total_xp = user_data['xp']
            old_level, _, _ = self.get_level_from_total_xp(old_total_xp)
            
            # Agregar XP
            new_total_xp = old_total_xp + xp_amount
            await add_user_xp(member.id, member.guild.id, xp_amount)
            
            # Verificar nuevo nivel
            new_level, _, _ = self.get_level_from_total_xp(new_total_xp)
            
            # Si subió de nivel
            if new_level > old_level:
                await self.handle_level_up(member, new_level, old_level)
                
        except Exception as e:
            print(f"Error en add_xp_and_check_levelup: {e}")
    
    async def handle_level_up(self, member: discord.Member, new_level: int, old_level: int):
        """Maneja la subida de nivel de un usuario"""
        try:
            # Obtener canal de anuncios
            channel = self.bot.get_channel(self.level_up_channel_id)
            if not channel:
                return

            # Verificar si es múltiplo de 10
            is_milestone = new_level % 10 == 0

            if is_milestone:
                # Buscar rol correspondiente
                role = None
                if new_level in self.level_roles:
                    role_id = self.level_roles[new_level]
                    role = member.guild.get_role(role_id)

                # Crear descripción con rol si existe
                if role:
                    description = (
                        f"{member.mention} ha alcanzado el **nivel {new_level}** "
                        f"y ha obtenido el rol {role.mention} 🎉"
                    )
                else:
                    description = f"{member.mention} ha alcanzado el **nivel {new_level}** 🎉"

                embed = discord.Embed(
                    title="🎉 ¡NIVEL ALCANZADO!",
                    description=description,
                    color=0x00ffff
                )

                # Asignar rol correspondiente
                await self.assign_level_role(member, new_level)

            else:
                # Mensaje sin mención de rol en otros niveles
                embed = discord.Embed(
                    title="⬆️ Subida de nivel",
                    description=f"**{member.display_name}** ha alcanzado el nivel **{new_level}**",
                    color=0x0099ff
                )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Nivel anterior", value=str(old_level), inline=True)
            embed.add_field(name="Nivel actual", value=str(new_level), inline=True)

            await channel.send(embed=embed)

        except Exception as e:
            print(f"Error en handle_level_up: {e}")

    
    async def assign_level_role(self, member: discord.Member, level: int):
        """Asigna el rol correspondiente al nivel y elimina el anterior"""
        try:
            if level not in self.level_roles:
                return
            
            new_role_id = self.level_roles[level]
            new_role = member.guild.get_role(new_role_id)
            
            if not new_role:
                print(f"No se encontró el rol {new_role_id} para el nivel {level}")
                return
            
            # Eliminar roles de niveles anteriores
            roles_to_remove = []
            for role in member.roles:
                if role.id in self.level_roles.values() and role.id != new_role_id:
                    roles_to_remove.append(role)
            
            # Remover roles antiguos
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason=f"Actualización de nivel a {level}")
            
            # Agregar nuevo rol
            await member.add_roles(new_role, reason=f"Alcanzó el nivel {level}")
            
            print(f"Asignado rol de nivel {level} a {member.display_name}")
            
        except Exception as e:
            print(f"Error asignando rol de nivel: {e}")
    
    # ================== COMANDOS DE USUARIO ==================
    
    @commands.command(name="xp")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def user_xp(self, ctx, member: discord.Member = None):
        """Ver tu experiencia actual o la de otro usuario"""
        if member is None:
            member = ctx.author
        
        if member.bot:
            embed = discord.Embed(
                title="⚠️ Error",
                description="Los bots no tienen experiencia.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Obtener datos del usuario
            user_data = await get_user_level_data(member.id, ctx.guild.id)
            if not user_data:
                embed = discord.Embed(
                    title="⚠️ Usuario no encontrado",
                    description=f"{member.mention} no tiene datos registrados.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            # Calcular nivel y progreso
            total_xp = user_data['xp']
            level, current_xp, next_level_xp = self.get_level_from_total_xp(total_xp)
            
            # Obtener ranking
            rank = await get_user_rank(member.id, ctx.guild.id)
            
            # Calcular porcentaje de progreso
            progress_percent = (current_xp / next_level_xp * 100) if next_level_xp > 0 else 100
            
            # Crear embed
            embed = discord.Embed(
                title=f"📊 Experiencia de {member.display_name}",
                color=0x00ffff
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            embed.add_field(name="🏆 Nivel", value=str(level), inline=True)
            embed.add_field(name="📈 Ranking", value=f"#{rank}", inline=True)
            embed.add_field(name="💎 XP Total", value=f"{total_xp:,}", inline=True)
            
            embed.add_field(
                name="📊 Progreso en nivel",
                value=f"{current_xp:,}/{next_level_xp:,} ({progress_percent:.1f}%)",
                inline=False
            )
            
            # Barra de progreso visual
            progress_bar_length = 20
            filled = int(progress_bar_length * (current_xp / next_level_xp))
            bar = "█" * filled + "░" * (progress_bar_length - filled)
            embed.add_field(name="⚡ Progreso", value=f"`{bar}`", inline=False)
            
            # XP faltante para siguiente nivel
            xp_needed = next_level_xp - current_xp
            embed.add_field(name="🎯 XP para siguiente nivel", value=f"{xp_needed:,}", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error en comando xp: {e}")
            embed = discord.Embed(
                title="⚠️ Error",
                description="Ocurrió un error al obtener la información.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="lb", aliases=["leaderboard", "ranking"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def leaderboard(self, ctx, period: str = None):
        """Ranking global de usuarios por XP"""
        try:
            # Determinar el período
            if period is None:
                title = "🏆 Ranking Global de XP"
                leaderboard_data = await get_leaderboard(ctx.guild.id, limit=10)
            elif period.lower() in ['s', 'semanal', 'semana', 'week', 'weekly']:
                title = "📅 Top XP - Esta Semana"
                leaderboard_data = await get_weekly_leaderboard(ctx.guild.id, limit=10)
            elif period.lower() in ['m', 'mensual', 'mes', 'month', 'monthly']:
                title = "📆 Top XP - Este Mes"
                leaderboard_data = await get_monthly_leaderboard(ctx.guild.id, limit=10)
            else:
                embed = discord.Embed(
                    title="⚠️ Período inválido",
                    description="Usa: `!lb` (global), `!lb s` (semanal), `!lb m` (mensual)",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title="📊 Ranking vacío",
                    description="No hay datos para mostrar.",
                    color=0xffaa00
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=title,
                color=0x00ffff
            )
            
            # Emojis para las primeras posiciones
            medals = ["🥇", "🥈", "🥉"]
            
            leaderboard_text = ""
            
            for i, user_data in enumerate(leaderboard_data, 1):
                user_id = user_data['user_id']
                xp = user_data['xp']
                
                # Obtener miembro del servidor
                member = ctx.guild.get_member(user_id)
                if not member:
                    continue
                
                # Calcular nivel
                level, _, _ = self.get_level_from_total_xp(xp)
                
                # Emoji para posición
                if i <= 3:
                    position_emoji = medals[i-1]
                else:
                    position_emoji = f"`{i}.`"
                
                # Formato de la entrada
                leaderboard_text += f"{position_emoji} **{member.display_name}** - Nivel {level} ({xp:,} XP)\n"
            
            if leaderboard_text:
                embed.description = leaderboard_text
            else:
                embed.description = "No se encontraron usuarios válidos."
            
            embed.set_footer(text=f"Mostrando top {len(leaderboard_data)} usuarios")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error en comando leaderboard: {e}")
            embed = discord.Embed(
                title="⚠️ Error",
                description="Ocurrió un error al obtener el ranking.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    # ================== COMANDOS DE ADMINISTRACIÓN ==================
    
    @commands.group(name="xpc", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def xp_commands(self, ctx):
        """Comandos para gestionar XP (Solo administradores)"""
        embed = discord.Embed(
            title="🎮 Comandos de XP - Administración",
            description="Comandos disponibles para gestionar experiencia:",
            color=0x00ffff
        )
        embed.add_field(
            name="📈 Agregar XP",
            value="`!xpc add <usuario> <cantidad>`",
            inline=False
        )
        embed.add_field(
            name="📉 Quitar XP",
            value="`!xpc remove <usuario> <cantidad>`",
            inline=False
        )
        embed.add_field(
            name="🔧 Establecer XP",
            value="`!xpc set <usuario> <cantidad>`",
            inline=False
        )
        embed.add_field(
            name="🏆 Establecer Nivel",
            value="`!xpc setlevel <usuario> <nivel>`",
            inline=False
        )
        embed.add_field(
            name="⚡ Multiplicador de Rol",
            value="`!xpc multiplier <rol> <multiplicador> <horas>`",
            inline=False
        )
        embed.add_field(
            name="🔍 Información de Debug",
            value="`!xpinfo <usuario>`",
            inline=False
        )
        await ctx.send(embed=embed)
    
    @xp_commands.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def add_xp_command(self, ctx, member: discord.Member, amount: int):
        """Agrega XP a un usuario"""
        if member.bot:
            embed = discord.Embed(
                title="⌚ Error",
                description="No puedes agregar XP a un bot.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if amount <= 0:
            embed = discord.Embed(
                title="⌚ Error",
                description="La cantidad debe ser mayor a 0.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            await self.add_xp_and_check_levelup(member, amount)
            
            embed = discord.Embed(
                title="✅ XP Agregada",
                description=f"Se agregaron **{amount:,} XP** a {member.mention}",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error agregando XP: {e}")
            embed = discord.Embed(
                title="⌚ Error",
                description="Ocurrió un error al agregar XP.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @xp_commands.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def remove_xp_command(self, ctx, member: discord.Member, amount: int):
        """Quita XP a un usuario"""
        if member.bot:
            embed = discord.Embed(
                title="⌚ Error",
                description="No puedes quitar XP a un bot.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if amount <= 0:
            embed = discord.Embed(
                title="⌚ Error",
                description="La cantidad debe ser mayor a 0.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Obtener XP actual
            user_data = await get_user_level_data(member.id, ctx.guild.id)
            if not user_data:
                embed = discord.Embed(
                    title="⌚ Error",
                    description="El usuario no tiene datos registrados.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            current_xp = user_data['xp']
            new_xp = max(0, current_xp - amount)
            
            await set_user_xp(member.id, ctx.guild.id, new_xp)
            
            embed = discord.Embed(
                title="✅ XP Removida",
                description=f"Se quitaron **{amount:,} XP** a {member.mention}",
                color=0x00ff00
            )
            embed.add_field(name="XP Total", value=f"{new_xp:,}", inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error quitando XP: {e}")
            embed = discord.Embed(
                title="⌚ Error",
                description="Ocurrió un error al quitar XP.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @xp_commands.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_command(self, ctx, member: discord.Member, amount: int):
        """Establece la XP de un usuario a un valor específico"""
        if member.bot:
            embed = discord.Embed(
                title="⌚ Error",
                description="No puedes establecer XP a un bot.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if amount < 0:
            embed = discord.Embed(
                title="⌚ Error",
                description="La cantidad no puede ser negativa.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            await set_user_xp(member.id, ctx.guild.id, amount)
            
            level, current_xp, next_xp = self.get_level_from_total_xp(amount)
            
            embed = discord.Embed(
                title="✅ XP Establecida",
                description=f"La XP de {member.mention} se estableció a **{amount:,}**",
                color=0x00ff00
            )
            embed.add_field(name="Nivel", value=str(level), inline=True)
            embed.add_field(name="Progreso", value=f"{current_xp}/{next_xp}", inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error estableciendo XP: {e}")
            embed = discord.Embed(
                title="⌚ Error",
                description="Ocurrió un error al establecer la XP.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @xp_commands.command(name="setlevel")
    @commands.has_permissions(manage_guild=True)
    async def set_level_command(self, ctx, member: discord.Member, level: int):
        """Establece el nivel de un usuario"""
        if member.bot:
            embed = discord.Embed(
                title="⌚ Error",
                description="No puedes establecer nivel a un bot.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if level < 1 or level > 200:
            embed = discord.Embed(
                title="⌚ Error",
                description="El nivel debe estar entre 1 y 200.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Calcular XP total necesaria para el nivel
            total_xp = self.get_total_xp_for_level(level)
            
            await set_user_xp(member.id, ctx.guild.id, total_xp)
            
            # Asignar rol si es múltiplo de 10
            if level % 10 == 0:
                await self.assign_level_role(member, level)
            
            embed = discord.Embed(
                title="✅ Nivel Establecido",
                description=f"El nivel de {member.mention} se estableció a **{level}**",
                color=0x00ff00
            )
            embed.add_field(name="XP Total", value=f"{total_xp:,}", inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error estableciendo nivel: {e}")
            embed = discord.Embed(
                title="⌚ Error",
                description="Ocurrió un error al establecer el nivel.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @xp_commands.command(name="multiplier")
    @commands.has_permissions(manage_guild=True)
    async def set_multiplier_command(self, ctx, role: discord.Role, multiplier: float, hours: int):
        """Aplica un multiplicador de XP a un rol por tiempo determinado"""
        if multiplier <= 0:
            embed = discord.Embed(
                title="⌚ Error",
                description="El multiplicador debe ser mayor a 0.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if hours <= 0:
            embed = discord.Embed(
                title="⌚ Error",
                description="Las horas deben ser mayores a 0.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            expires_at = datetime.now() + timedelta(hours=hours)
            
            self.xp_multipliers[role.id] = {
                'multiplier': multiplier,
                'expires': expires_at
            }
            
            embed = discord.Embed(
                title="✅ Multiplicador Aplicado",
                description=f"Multiplicador de **{multiplier}x** aplicado al rol {role.mention}",
                color=0x00ff00
            )
            embed.add_field(name="Duración", value=f"{hours} horas", inline=True)
            embed.add_field(name="Expira", value=expires_at.strftime("%d/%m/%Y %H:%M"), inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error aplicando multiplicador: {e}")
            embed = discord.Embed(
                title="⌚ Error",
                description="Ocurrió un error al aplicar el multiplicador.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    # ================== FUNCIONES DEL PERFIL ==================
    
    def get_user_rank_role(self, member):
        """Obtiene el rol de rango del usuario (que empiece con ◈ Rango)"""
        for role in member.roles:
            if role.name.startswith("◈ Rango"):
                return role.name.replace("◈ ", "")
        return "Sin Rango"
    
    async def get_user_avatar(self, user):
        """Descarga el avatar del usuario"""
        try:
            async with aiohttp.ClientSession() as session:
                avatar_url = user.display_avatar.url
                async with session.get(avatar_url) as resp:
                    avatar_data = await resp.read()
                    return Image.open(io.BytesIO(avatar_data)).convert('RGBA')
        except:
            # Avatar por defecto si no se puede descargar
            return Image.new('RGBA', (128, 128), (100, 100, 100, 255))
    
    def get_font(self, size: int, bold: bool = False):
        """Obtiene una fuente con el tamaño especificado"""
        try:
            # Primero intentar cargar la fuente Orbitron específica
            orbitron_path = "resources/fonts/Orbitron-Medium.ttf"
            if os.path.exists(orbitron_path):
                return ImageFont.truetype(orbitron_path, size)
            
            # Intentar otras variantes de Orbitron
            orbitron_variants = [
                "resources/fonts/Orbitron-Bold.ttf",
                "resources/fonts/Orbitron-Regular.ttf",
                "resources/fonts/Orbitron.ttf"
            ]
            
            for variant in orbitron_variants:
                if os.path.exists(variant):
                    return ImageFont.truetype(variant, size)
            
            # Fallback a fuentes genéricas si Orbitron no está disponible
            if bold:
                font_files = ['bold.ttf', 'arial-bold.ttf', 'roboto-bold.ttf', 'font-bold.ttf']
                for font_file in font_files:
                    font_path = f"{self.font_path}/{font_file}"
                    if os.path.exists(font_path):
                        return ImageFont.truetype(font_path, size)
            else:
                font_files = ['regular.ttf', 'arial.ttf', 'roboto.ttf', 'font.ttf']
                for font_file in font_files:
                    font_path = f"{self.font_path}/{font_file}"
                    if os.path.exists(font_path):
                        return ImageFont.truetype(font_path, size)
        except Exception as e:
            print(f"Error cargando fuente: {e}")
        
        # Fuente por defecto si no encuentra ninguna personalizada
        return ImageFont.load_default()
    
    def create_rounded_rectangle(self, width: int, height: int, radius: int, color: tuple):
        """Crea un rectángulo con esquinas redondeadas"""
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=radius,
            fill=color
        )
        
        return img
    
    def create_circle_avatar(self, avatar_img: Image, size: int):
        """Convierte el avatar en circular"""
        avatar_img = avatar_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Crear máscara circular
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # Aplicar máscara
        result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        result.paste(avatar_img, (0, 0))
        result.putalpha(mask)
        
        return result
    
    def draw_progress_bar(self, draw, x: int, y: int, width: int, height: int, 
                         progress: float, bg_color: tuple, fill_color: tuple, radius: int = 15):
        """Dibuja una barra de progreso con el estilo de la imagen"""
        # Fondo de la barra (más oscuro)
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=bg_color
        )
        
        # Barra de progreso (cyan brillante)
        if progress > 0:
            progress_width = int(width * progress)
            if progress_width > radius * 2:
                draw.rounded_rectangle(
                    [(x, y), (x + progress_width, y + height)],
                    radius=radius,
                    fill=fill_color
                )
    
    async def create_profile_image(self, user, user_data: dict, balance: float, rank: int):
        """Crea la imagen del perfil con el diseño exacto y DATOS CORRECTOS"""
        # Dimensiones exactas especificadas
        width, height = 820, 950
        
        # Crear imagen base con fondo azul oscuro como en la imagen
        try:
            # Intentar cargar fondo personalizado
            background = Image.open(f"{self.bg_path}/perfil.png").resize((width, height))
        except Exception as e:
            print(f"No se pudo cargar la imagen de fondo: {e}")
            # Fondo azul oscuro como en la imagen
            background = Image.new('RGB', (width, height), (20, 35, 60))  # Color azul oscuro
            
        background = background.convert('RGBA')
        draw = ImageDraw.Draw(background)
        
        # Colores exactos de la imagen
        cyan_bright = (0, 255, 255)  # Cyan brillante
        cyan_dark = (0, 180, 200)    # Cyan más oscuro
        dark_blue = (15, 25, 45)     # Azul muy oscuro para fondos
        darker_blue = (10, 20, 35)   # Azul aún más oscuro
        white_text = (255, 255, 255) # Texto blanco
        
        # ===== USAR ÚNICA FUNCIÓN PARA CALCULAR NIVEL =====
        total_xp = user_data['xp']
        level, current_xp, next_level_xp = self.get_level_from_total_xp(total_xp)
        
        print(f"DEBUG: Usuario {user.name} - XP Total: {total_xp}, Nivel: {level}, XP en nivel: {current_xp}/{next_level_xp}")
        
        # Obtener rol de rango del usuario
        user_rank_role = self.get_user_rank_role(user)
        
        # Descargar y procesar avatar
        avatar = await self.get_user_avatar(user)
        
        # === LAYOUT ADAPTADO PARA 820x950 ===
        
        # Avatar en la parte superior centrado - más grande para la resolución
        avatar_size = 220
        avatar_circular = self.create_circle_avatar(avatar, avatar_size)
        avatar_x = (width - avatar_size) - 542 
        avatar_y = 49
        
        # Borde cyan alrededor del avatar
        draw.ellipse(
            [(avatar_x - 5, avatar_y - 5), (avatar_x + avatar_size + 5, avatar_y + avatar_size + 5)],
            outline=cyan_bright,
            width=0
        )
        
        background.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)
        
        # Fuentes más grandes para la resolución 820x950
        font_huge = self.get_font(54, bold=True)    # Para el nombre
        font_large = self.get_font(40, bold=True)   # Para nivel
        font_medium = self.get_font(60, bold=True)  # Para textos importantes
        font_small = self.get_font(20)              # Para detalles
        font_role = self.get_font(45, bold=True)    # Para el rol de rango
        
        # === INFORMACIÓN DEL USUARIO (DEBAJO DEL AVATAR) ===
        
        info_y = avatar_y + 40
        
        # Nombre del usuario centrado
        username = user.name
        if len(username) > 15:
            username = username[:12] + "..."
        
        # Calcular posición centrada para el texto
        bbox = draw.textbbox((0, 0), username, font=font_huge)
        text_width = bbox[2] - bbox[0]
        username_x = (width - text_width) + -190

        draw.text((username_x, info_y + 10), username, font=font_huge, fill=cyan_bright)
        
        # Nivel centrado
        level_text = f"{level}"
        bbox = draw.textbbox((0, 0), level_text, font=font_role)
        text_width = bbox[2] - bbox[0]
        level_x = (width - text_width) -93
        level_y = info_y + 112

        draw.text((level_x, level_y), level_text, font=font_role, fill=cyan_bright)
        
        # Rol de rango a la misma altura del nivel pero 295px más a la izquierda
        role_x = level_x - 295
        role_y = level_y - 2
        
        # Acortar el texto del rol si es muy largo
        role_text = user_rank_role
        if len(role_text) > 12:
            role_text = role_text[:9] + "..."
        
        draw.text((role_x, role_y), role_text, font=font_role, fill=cyan_bright)
        
        # === UNA SOLA BARRA DE PROGRESO ===
        
        progress_y = info_y + 240
        
        # Barra de progreso de XP - USANDO DATOS CORRECTOS
        progress = current_xp / next_level_xp if next_level_xp > 0 else 1.0
        
        bar_width = width - 119
        bar_height = 46
        bar_x = 57
        
        self.draw_progress_bar(
            draw, bar_x, progress_y, bar_width, bar_height, progress,
            bg_color=darker_blue,
            fill_color=cyan_bright,
            radius=18
        )
        
        # Texto "EXP" a la izquierda de la experiencia
        exp_label_x = bar_x
        exp_label_y = progress_y + bar_height + 15
        draw.text((exp_label_x, exp_label_y), "EXP", font=font_small, fill=white_text)
        
        # Experiencia (750/1000) abajo izquierda de la barra - DATOS CORRECTOS
        exp_text = f"{current_xp}/{next_level_xp}"
        exp_text_x = exp_label_x + 60  # Después del texto "EXP"
        draw.text((exp_text_x, exp_label_y), exp_text, font=font_small, fill=white_text)
        
        # === DINERO Y RANK ===
        
        money_y = progress_y + bar_height + 367
        
        # Dinero
        money_text = f"{balance:.2f}"
        bbox = draw.textbbox((0, 0), money_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        money_x = (width - text_width) - 428
        draw.text((money_x, money_y), money_text, font=font_medium, fill=cyan_bright)
        
        # Rank en formato #2
        rank_text = f"#{rank}"
        bbox = draw.textbbox((0, 0), rank_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        rank_x = (width - text_width) -150
        rank_y = money_y + 35
        draw.text((rank_x, rank_y), rank_text, font=font_medium, fill=cyan_bright)
        
        return background
    
    @commands.command(name="perfil", aliases=["profile", "p"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def perfil(self, ctx, member: discord.Member = None):
        """Muestra el perfil de un usuario con imagen personalizada"""
        
        if member is None:
            member = ctx.author
        
        if member.bot:
            embed = discord.Embed(
                title="⚠️ Error",
                description="No puedo mostrar el perfil de un bot.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Obtener datos del usuario
            user_data = await get_user_level_data(member.id, ctx.guild.id)
            if not user_data:
                embed = discord.Embed(
                    title="⚠️ Usuario no encontrado",
                    description=f"{member.mention} no tiene datos registrados en el sistema de niveles.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            # Obtener balance del usuario
            balance = await get_user_balance(member.id)
            
            # Obtener ranking del usuario
            rank = await get_user_rank(member.id, ctx.guild.id)
            
            # DEBUG: Mostrar datos obtenidos
            total_xp = user_data['xp']
            level, current_xp, next_level_xp = self.get_level_from_total_xp(total_xp)
            print(f"PERFIL DEBUG: {member.name} - XP: {total_xp}, Nivel calculado: {level}")
            
            # Crear imagen del perfil - SIN guild_config
            profile_img = await self.create_profile_image(
                member, user_data, float(balance), rank
            )
            
            # Convertir imagen a bytes
            img_buffer = io.BytesIO()
            profile_img.save(img_buffer, format='PNG', quality=95)
            img_buffer.seek(0)
            
            # Crear archivo de Discord
            file = discord.File(img_buffer, filename=f"perfil_{member.id}.png")
            
            # Enviar solo la imagen, sin embed
            await ctx.send(file=file)
            
        except Exception as e:
            print(f"Error en comando perfil: {e}")
            
            embed = discord.Embed(
                title="⚠️ Error",
                description="Ocurrió un error al generar el perfil. Inténtalo de nuevo más tarde.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @perfil.error
    async def perfil_error(self, ctx, error):
        """Maneja errores del comando perfil"""
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Cooldown",
                description=f"Debes esperar {error.retry_after:.0f} segundos antes de usar este comando de nuevo.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
    
    # ================== COMANDO DE DEBUG ==================
    
    @commands.command(name="xpinfo")
    @commands.has_permissions(manage_guild=True)
    async def xp_info(self, ctx, member: discord.Member = None):
        """Comando de debug para verificar XP y nivel de un usuario"""
        if member is None:
            member = ctx.author
        
        try:
            user_data = await get_user_level_data(member.id, ctx.guild.id)
            if not user_data:
                await ctx.send("⌚ Usuario no encontrado en la base de datos")
                return
            
            total_xp = user_data['xp']
            level, current_xp, next_level_xp = self.get_level_from_total_xp(total_xp)
            
            embed = discord.Embed(
                title=f"🔍 Información XP de {member.display_name}",
                color=0x00ffff
            )
            embed.add_field(name="XP Total", value=f"{total_xp:,}", inline=True)
            embed.add_field(name="Nivel Calculado", value=str(level), inline=True)
            embed.add_field(name="XP en Nivel Actual", value=f"{current_xp:,}", inline=True)
            embed.add_field(name="XP para Siguiente Nivel", value=f"{next_level_xp:,}", inline=True)
            embed.add_field(name="Progreso", value=f"{current_xp}/{next_level_xp}", inline=True)
            embed.add_field(name="XP Acumulada hasta Nivel", value=f"{self.cumulative_xp.get(level, 0):,}", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"⌚ Error: {e}")
    
    # ================== MANEJO DE ERRORES ==================
    
    @user_xp.error
    async def xp_error(self, ctx, error):
        """Maneja errores del comando xp"""
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Cooldown",
                description=f"Debes esperar {error.retry_after:.0f} segundos antes de usar este comando de nuevo.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)
    
    @leaderboard.error
    async def leaderboard_error(self, ctx, error):
        """Maneja errores del comando leaderboard"""
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Cooldown",
                description=f"Debes esperar {error.retry_after:.0f} segundos antes de usar este comando de nuevo.",
                color=0xffaa00
            )
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    # Crear directorios necesarios
    os.makedirs("resources/fonts", exist_ok=True)
    os.makedirs("resources/images/perfil", exist_ok=True)
    
    await bot.add_cog(LevelsSystem(bot))