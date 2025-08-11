import discord
from discord.ext import commands, tasks
import json
import asyncio
import time
import math
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import aiohttp
import os
import random
import logging

# Importar funciones de la base de datos
import database

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LevelCalculator:
    @staticmethod
    def calculate_level(xp, formula='exponential'):
        """Calcula el nivel basado en la XP (1-200)"""
        if formula == 'exponential':
            # Fórmula optimizada para 200 niveles
            level = int(math.sqrt(xp / 50)) + 1
            return min(level, 200)
        elif formula == 'linear':
            level = int(xp / 10000) + 1
            return min(level, 200)
        elif formula == 'logarithmic':
            if xp <= 0:
                return 1
            level = int(10 * math.log10(xp + 1)) + 1
            return min(level, 200)
        else:
            level = int(math.sqrt(xp / 50)) + 1
            return min(level, 200)
    
    @staticmethod
    def calculate_xp_for_level(level, formula='exponential'):
        """Calcula la XP necesaria para un nivel específico"""
        if level > 200:
            level = 200
        if level < 1:
            level = 1
            
        if formula == 'exponential':
            return ((level - 1) ** 2) * 50
        elif formula == 'linear':
            return (level - 1) * 10000
        elif formula == 'logarithmic':
            return int((10 ** ((level - 1) / 10)) - 1)
        else:
            return ((level - 1) ** 2) * 50
    
    @staticmethod
    def get_xp_for_next_level(current_xp, formula='exponential'):
        """Obtiene la XP necesaria para el siguiente nivel"""
        current_level = LevelCalculator.calculate_level(current_xp, formula)
        if current_level >= 200:
            return LevelCalculator.calculate_xp_for_level(200, formula)
        next_level_xp = LevelCalculator.calculate_xp_for_level(current_level + 1, formula)
        return next_level_xp

class ProfileImageGenerator:
    def __init__(self):
        self.template_path = r"resources\images\level.png"
        self.pixel_fonts = [
            r"resources\fonts\pixel.ttf",
        ]
    
    def load_pixel_font(self, size):
        """Carga una fuente estilo pixel art"""
        for font_path in self.pixel_fonts:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        try:
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def draw_rounded_rectangle(self, draw, xy, radius, fill=None, outline=None, width=1):
        """Dibuja un rectángulo con bordes redondeados"""
        x1, y1, x2, y2 = xy
        
        # Dibujar rectángulo principal
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
        
        # Dibujar esquinas redondeadas
        draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill, outline=outline, width=width)
        draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill, outline=outline, width=width)
        draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill, outline=outline, width=width)
        draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill, outline=outline, width=width)
    
    async def generate_profile_image(self, user, user_data, rank, guild_name=""):
        """Genera una imagen de perfil moderna y profesional"""
        try:
            # Crear imagen base con gradiente mejorado
            img = Image.new('RGBA', (800, 300), color=(0, 0, 0, 0))
            
            # Crear gradiente de fondo más dinámico
            gradient = Image.new('RGBA', (800, 300), color=(0, 0, 0, 0))
            grad_draw = ImageDraw.Draw(gradient)
            
            # Gradiente basado en el nivel del usuario
            level = user_data['level']
            if level >= 100:
                # Gradiente dorado para niveles altos
                base_color = (40, 35, 20)
                accent_color = (80, 65, 30)
            elif level >= 50:
                # Gradiente púrpura para niveles medios
                base_color = (35, 25, 45)
                accent_color = (60, 40, 70)
            else:
                # Gradiente azul para niveles bajos
                base_color = (20, 25, 45)
                accent_color = (35, 45, 70)
            
            for y in range(300):
                ratio = y / 300
                r = int(base_color[0] + (accent_color[0] - base_color[0]) * ratio)
                g = int(base_color[1] + (accent_color[1] - base_color[1]) * ratio)
                b = int(base_color[2] + (accent_color[2] - base_color[2]) * ratio)
                grad_draw.line([(0, y), (800, y)], fill=(r, g, b, 255))
            
            # Añadir patrón de puntos para textura
            for i in range(0, 800, 50):
                for j in range(0, 300, 50):
                    alpha = random.randint(10, 30)
                    grad_draw.ellipse([i, j, i+2, j+2], fill=(255, 255, 255, alpha))
            
            img = gradient
            draw = ImageDraw.Draw(img)
            
            # Cargar fuentes mejoradas
            try:
                font_large = ImageFont.truetype("arial.ttf", 32)
                font_medium = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 18)
                font_tiny = ImageFont.truetype("arial.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_tiny = ImageFont.load_default()
            
            # Avatar con efectos mejorados
            avatar_url = str(user.display_avatar.url)
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as resp:
                    avatar_bytes = await resp.read()

            avatar = Image.open(io.BytesIO(avatar_bytes)).convert('RGBA')
            avatar_size = 130
            avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            
            # Crear máscara circular
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            circular_avatar = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
            circular_avatar.paste(avatar, (0, 0), mask=mask)
            
            # Borde del avatar basado en el nivel
            border_size = avatar_size + 12
            border_color = (255, 215, 0, 200) if level >= 100 else (138, 43, 226, 200) if level >= 50 else (30, 144, 255, 200)
            
            border_mask = Image.new('L', (border_size, border_size), 0)
            border_draw = ImageDraw.Draw(border_mask)
            border_draw.ellipse((0, 0, border_size, border_size), fill=255)
            
            border_img = Image.new('RGBA', (border_size, border_size), border_color)
            border_img.putalpha(border_mask)
            
            # Posicionar avatar
            avatar_x, avatar_y = 40, 85
            img.paste(border_img, (avatar_x - 6, avatar_y - 6), border_img)
            img.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
            
            # Información del usuario
            username = user.display_name[:20]
            text_start_x = avatar_x + avatar_size + 40
            
            # Nombre con sombra mejorada
            name_y = avatar_y + 15
            draw.text((text_start_x + 3, name_y + 3), username, font=font_large, fill=(0, 0, 0, 150))
            draw.text((text_start_x, name_y), username, font=font_large, fill=(255, 255, 255, 255))
            
            # Nivel con colores dinámicos
            level_text = f"Nivel {user_data['level']}"
            level_color = (255, 215, 0, 255) if level >= 100 else (138, 43, 226, 255) if level >= 50 else (0, 255, 255, 255)
            level_y = name_y + 45
            
            draw.text((text_start_x + 2, level_y + 2), level_text, font=font_medium, fill=(0, 0, 0, 120))
            draw.text((text_start_x, level_y), level_text, font=font_medium, fill=level_color)
            
            # Barra de progreso mejorada
            current_level_xp = LevelCalculator.calculate_xp_for_level(user_data['level'])
            if user_data['level'] >= 200:
                next_level_xp = current_level_xp
                progress_xp = 0
                needed_xp = 0
                progress_percentage = 1.0
            else:
                next_level_xp = LevelCalculator.calculate_xp_for_level(user_data['level'] + 1)
                progress_xp = user_data['xp'] - current_level_xp
                needed_xp = next_level_xp - current_level_xp
                progress_percentage = progress_xp / needed_xp if needed_xp > 0 else 1.0
            
            # Barra de progreso más elaborada
            bar_x = text_start_x
            bar_y = level_y + 45
            bar_width = 400
            bar_height = 25
            border_radius = 12
            
            # Sombra de la barra
            shadow_offset = 3
            self.draw_rounded_rectangle(
                draw,
                [bar_x + shadow_offset, bar_y + shadow_offset, bar_x + bar_width + shadow_offset, bar_y + bar_height + shadow_offset],
                border_radius,
                fill=(0, 0, 0, 80)
            )
            
            # Fondo de la barra
            self.draw_rounded_rectangle(
                draw,
                [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                border_radius,
                fill=(30, 30, 35, 255),
                outline=(60, 60, 70, 255),
                width=2
            )
            
            # Barra de progreso con gradiente dinámico
            if progress_percentage > 0:
                progress_width = int(bar_width * progress_percentage)
                
                progress_img = Image.new('RGBA', (progress_width, bar_height), color=(0, 0, 0, 0))
                prog_draw = ImageDraw.Draw(progress_img)
                
                # Gradiente basado en el nivel
                for x in range(progress_width):
                    ratio = x / progress_width if progress_width > 0 else 0
                    if level >= 100:
                        # Gradiente dorado
                        r = int(255 * (1 - ratio) + 218 * ratio)
                        g = int(215 * (1 - ratio) + 165 * ratio)
                        b = int(0 * (1 - ratio) + 32 * ratio)
                    elif level >= 50:
                        # Gradiente púrpura
                        r = int(138 * (1 - ratio) + 75 * ratio)
                        g = int(43 * (1 - ratio) + 0 * ratio)
                        b = int(226 * (1 - ratio) + 130 * ratio)
                    else:
                        # Gradiente azul
                        r = int(0 * (1 - ratio) + 30 * ratio)
                        g = int(191 * (1 - ratio) + 144 * ratio)
                        b = int(255 * (1 - ratio) + 255 * ratio)
                    
                    prog_draw.line([(x, 0), (x, bar_height)], fill=(r, g, b, 255))
                
                # Máscara para la barra de progreso
                progress_mask = Image.new('L', (progress_width, bar_height), 0)
                progress_mask_draw = ImageDraw.Draw(progress_mask)
                self.draw_rounded_rectangle(
                    progress_mask_draw,
                    [0, 0, progress_width, bar_height],
                    border_radius,
                    fill=255
                )
                
                progress_img.putalpha(progress_mask)
                img.paste(progress_img, (bar_x, bar_y), progress_img)
                
                # Efecto de brillo
                highlight_height = bar_height // 2
                highlight_img = Image.new('RGBA', (progress_width, highlight_height), color=(255, 255, 255, 80))
                highlight_mask = Image.new('L', (progress_width, highlight_height), 0)
                highlight_mask_draw = ImageDraw.Draw(highlight_mask)
                self.draw_rounded_rectangle(
                    highlight_mask_draw,
                    [0, 0, progress_width, highlight_height],
                    border_radius // 2,
                    fill=255
                )
                highlight_img.putalpha(highlight_mask)
                img.paste(highlight_img, (bar_x, bar_y + 3), highlight_img)
            
            # Texto de XP centrado sobre la barra
            if user_data['level'] >= 200:
                xp_text = "¡NIVEL MÁXIMO ALCANZADO!"
                xp_color = (255, 215, 0, 255)  # Dorado
            else:
                xp_text = f"{progress_xp:,} / {needed_xp:,} XP"
                xp_color = (220, 220, 220, 255)  # Gris claro
            
            # Calcular posición centrada
            text_bbox = draw.textbbox((0, 0), xp_text, font=font_small)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = bar_x + (bar_width - text_width) // 2
            text_y = bar_y + (bar_height - (text_bbox[3] - text_bbox[1])) // 2
            
            # Sombra del texto
            draw.text((text_x + 1, text_y + 1), xp_text, font=font_small, fill=(0, 0, 0, 150))
            # Texto principal
            draw.text((text_x, text_y), xp_text, font=font_small, fill=xp_color)
            
            # Ranking en esquina superior derecha
            rank_text = f"#{rank}"
            rank_bbox = draw.textbbox((0, 0), rank_text, font=font_medium)
            rank_width = rank_bbox[2] - rank_bbox[0]
            rank_height = rank_bbox[3] - rank_bbox[1]
            
            # Posición del ranking
            rank_x = 800 - rank_width - 40
            rank_y = 30
            padding = 12
            
            # Fondo del ranking con sombra
            shadow_x, shadow_y = rank_x - padding + 2, rank_y - padding//2 + 2
            self.draw_rounded_rectangle(
                draw,
                [shadow_x, shadow_y, shadow_x + rank_width + padding*2, shadow_y + rank_height + padding],
                8,
                fill=(0, 0, 0, 80)  # Sombra
            )
            
            # Fondo dorado del ranking
            bg_x, bg_y = rank_x - padding, rank_y - padding//2
            self.draw_rounded_rectangle(
                draw,
                [bg_x, bg_y, bg_x + rank_width + padding*2, bg_y + rank_height + padding],
                8,
                fill=(255, 215, 0, 220),  # Dorado semi-transparente
                outline=(255, 195, 0, 255),
                width=2
            )
            
            # Texto del ranking
            draw.text((rank_x, rank_y), rank_text, font=font_medium, fill=(30, 30, 30, 255))  # Negro suave
            
            # Información adicional en la parte inferior
            info_y = bar_y + bar_height + 25
            
            # Total de mensajes
            messages_text = f"Mensajes: {user_data['total_messages']:,}"
            draw.text((text_start_x + 1, info_y + 1), messages_text, font=font_tiny, fill=(0, 0, 0, 100))  # Sombra
            draw.text((text_start_x, info_y), messages_text, font=font_tiny, fill=(160, 160, 160, 255))
            
            # Progreso hacia nivel máximo (esquina derecha)
            if user_data['level'] < 200:
                progress_text = f"{user_data['level']}/200 ({(user_data['level']/200)*100:.1f}%)"
                progress_bbox = draw.textbbox((0, 0), progress_text, font=font_tiny)
                progress_width_text = progress_bbox[2] - progress_bbox[0]
                
                draw.text((800 - progress_width_text - 39, info_y + 1), progress_text, font=font_tiny, fill=(0, 0, 0, 100))  # Sombra
                draw.text((800 - progress_width_text - 40, info_y), progress_text, font=font_tiny, fill=(160, 160, 160, 255))
            
            # Línea divisoria sutil
            line_y = info_y - 10
            draw.line([(text_start_x, line_y), (750, line_y)], fill=(80, 80, 80, 150), width=1)
            
            # Convertir a bytes para enviar
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', quality=95)
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            print(f"Error generando imagen de perfil: {e}")
            return None

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.image_generator = ProfileImageGenerator()
        self.reset_weekly_xp.start()
        self.reset_monthly_xp.start()
        
        # 🔧 CONFIGURACIÓN PREDEFINIDA - EDITA ESTOS VALORES
        self.GUILD_CONFIGS = {
            # Reemplaza GUILD_ID con el ID de tu servidor
            1400106792196898886: {  # <-- CAMBIA ESTE ID POR EL DE TU SERVIDOR
                'level_up_channel': 1400106793249538048,  # <-- ID del canal de notificaciones
                'xp_per_message': 25,  # Aumentado para llegar a nivel 200
                'xp_cooldown': 60,  # segundos
                'xp_multiplier': 1.0,
                'level_formula': 'exponential',  # Optimizada para 200 niveles
                'enabled_channels': [],  # IDs de canales donde se gana XP (vacío = todos)
                'disabled_channels': [111111111111111111],  # IDs de canales sin XP
                'level_roles': {
                    # Roles cada 10 niveles - Configura los IDs de tus roles aquí
                    10: 1400106792196898893,   # Rol Nivel 10
                    20: 1400106792196898894,   # Rol Nivel 20
                    30: 1400106792196898895,   # Rol Nivel 30
                    40: 1400106792226127914,   # Rol Nivel 40
                    50: 1400106792226127915,   # Rol Nivel 50
                    60: 1400106792226127916,   # Rol Nivel 60
                    70: 1400106792226127917,   # Rol Nivel 70
                    80: 1400106792226127918,   # Rol Nivel 80
                    90: 1400106792226127919,   # Rol Nivel 90
                    100: 1400106792226127920,  # Rol Nivel 100
                    110: 1400106792226127921,  # Rol Nivel 110
                    120: 1400106792226127922,  # Rol Nivel 120
                    130: 1400106792226127923,  # Rol Nivel 130
                    140: 1400106792280658061,  # Rol Nivel 140
                    150: 1400106792280658062,  # Rol Nivel 150
                    160: 1400106792280658063,  # Rol Nivel 160
                    170: 1400106792280658064,  # Rol Nivel 170
                    180: 1400106792280658065,  # Rol Nivel 180
                    190: 1400106792280658066,  # Rol Nivel 190
                    200: 1400106792280658067,  # Rol Nivel 200 (Máximo)
                }
            },
        }
        
        # Inicializar configuraciones al cargar el cog
        self.bot.loop.create_task(self.initialize_guild_configs())
    
    def cog_unload(self):
        self.reset_weekly_xp.cancel()
        self.reset_monthly_xp.cancel()
    
    async def initialize_guild_configs(self):
        """Inicializa las configuraciones predefinidas en la base de datos"""
        await self.bot.wait_until_ready()
        
        for guild_id, config in self.GUILD_CONFIGS.items():
            # Verificar si el servidor existe
            guild = self.bot.get_guild(guild_id)
            if not guild:
                print(f"⚠️ Servidor con ID {guild_id} no encontrado")
                continue
            
            print(f"🔧 Configurando servidor: {guild.name}")
            
            # Configurar ajustes básicos del servidor
            await database.update_guild_config(
                guild_id,
                level_up_channel=config['level_up_channel'],
                xp_per_message=config['xp_per_message'],
                xp_cooldown=config['xp_cooldown'],
                enabled_channels=config['enabled_channels'],
                disabled_channels=config['disabled_channels'],
                xp_multiplier=config['xp_multiplier'],
                level_formula=config['level_formula']
            )
            
            # Configurar roles por nivel
            for level, role_id in config['level_roles'].items():
                # Verificar que el rol existe
                role = guild.get_role(role_id)
                if role:
                    await database.set_level_role(guild_id, level, role_id)
            
            # Verificar canal de notificaciones
            channel = guild.get_channel(config['level_up_channel'])
            if channel:
                print(f"  ✅ Canal de notificaciones: {channel.name}")
            else:
                print(f"  ❌ Canal con ID {config['level_up_channel']} no encontrado")
            
            print(f"✅ Configuración completada para {guild.name}\n")
    
    def get_predefined_config(self, guild_id):
        """Obtiene la configuración predefinida para un servidor"""
        return self.GUILD_CONFIGS.get(guild_id, {
            'level_up_channel': None,
            'xp_per_message': 15,
            'xp_cooldown': 60,
            'enabled_channels': [],
            'disabled_channels': [],
            'xp_multiplier': 1.0,
            'level_formula': 'exponential',
            'level_roles': {}
        })
    
    @tasks.loop(hours=168)  # Cada semana
    async def reset_weekly_xp(self):
        """Resetea la XP semanal"""
        await database.reset_weekly_xp()
    
    @tasks.loop(hours=720)  # Cada mes (30 días)
    async def reset_monthly_xp(self):
        """Resetea la XP mensual"""
        await database.reset_monthly_xp()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listener para mensajes - otorga XP"""
        if message.author.bot or not message.guild:
            return
        
        # Usar configuración predefinida si existe, sino la de la base de datos
        predefined_config = self.get_predefined_config(message.guild.id)
        if predefined_config and predefined_config.get('level_up_channel'):
            guild_config = predefined_config
        else:
            guild_config = await database.get_guild_level_config(message.guild.id)
        
        # Verificar si el canal está habilitado para XP
        if guild_config['enabled_channels'] and message.channel.id not in guild_config['enabled_channels']:
            return
        
        if message.channel.id in guild_config['disabled_channels']:
            return
        
        user_data = await database.get_user_level_data(message.author.id, message.guild.id)
        current_time = int(time.time())
        
        # Verificar cooldown
        if user_data and current_time - user_data['last_xp_time'] < guild_config['xp_cooldown']:
            return
        
        # Calcular XP a otorgar
        base_xp = guild_config['xp_per_message']
        xp_gain = int(base_xp * guild_config['xp_multiplier'])
        
        # Actualizar XP
        await database.update_user_xp(message.author.id, message.guild.id, xp_gain, xp_gain, xp_gain)
        
        # Verificar subida de nivel
        updated_data = await database.get_user_level_data(message.author.id, message.guild.id)
        new_level = LevelCalculator.calculate_level(updated_data['xp'], guild_config['level_formula'])
        
        if new_level > updated_data['level']:
            await database.update_user_level(message.author.id, message.guild.id, new_level)
            await self.handle_level_up(message.author, message.guild, new_level, guild_config)
    
    async def handle_level_up(self, user, guild, new_level, guild_config):
        """Maneja la subida de nivel de un usuario"""
        # Determinar si es un nivel especial (cada 10 niveles)
        is_role_level = new_level % 10 == 0
        
        # Enviar notificación
        if guild_config['level_up_channel']:
            channel = guild.get_channel(guild_config['level_up_channel'])
            if channel:
                embed = discord.Embed(
                    title="🎉 ¡Subida de Nivel!",
                    description=f"{user.mention} ha subido al **nivel {new_level}/200**!",
                    color=0x00ff00
                )
                
                # Agregar información especial para niveles con roles
                if is_role_level:
                    embed.add_field(name="🏆 ¡Rol Desbloqueado!", value=f"¡Has desbloqueado un nuevo rol por alcanzar el nivel {new_level}!", inline=False)
                    embed.color = 0xffd700  # Color dorado para niveles especiales
                
                # Mostrar progreso hacia nivel 200
                if new_level == 200:
                    embed.add_field(name="👑 NIVEL MÁXIMO", value="¡Has alcanzado el nivel máximo del servidor!", inline=False)
                    embed.color = 0xff0000  # Color rojo para nivel máximo
                else:
                    progress_percentage = (new_level / 200) * 100
                    embed.add_field(name="📊 Progreso Global", value=f"{progress_percentage:.1f}% hacia el nivel máximo (200)", inline=False)
                
                embed.set_thumbnail(url=user.display_avatar.url)
                await channel.send(embed=embed)
        
        # Manejar roles por nivel usando configuración predefinida
        predefined_config = self.get_predefined_config(guild.id)
        level_roles = predefined_config.get('level_roles', {})
        
        # Si no hay configuración predefinida, usar la de la base de datos
        if not level_roles:
            level_roles = await database.get_level_roles(guild.id)
        
        if new_level in level_roles:
            role = guild.get_role(level_roles[new_level])
            if role:
                # Remover roles de niveles anteriores (solo roles cada 10 niveles)
                for level in range(10, new_level, 10):  # 10, 20, 30... hasta new_level-10
                    if level in level_roles:
                        old_role = guild.get_role(level_roles[level])
                        if old_role and old_role in user.roles:
                            await user.remove_roles(old_role)
                            print(f"🔄 Removido rol {old_role.name} de {user.display_name}")
                
                # Agregar nuevo rol
                await user.add_roles(role)
                print(f"✅ Agregado rol {role.name} a {user.display_name} (Nivel {new_level})")
                
                # Notificar por DM si es necesario
                try:
                    embed = discord.Embed(
                        title="🔓 Contenido Desbloqueado",
                        description=f"¡Has alcanzado el nivel {new_level} y has desbloqueado el rol **{role.name}**!",
                        color=0x00ff00
                    )
                    
                    # Información adicional para nivel máximo
                    if new_level == 200:
                        embed.add_field(name="👑 ¡Felicitaciones!", value="Has alcanzado el nivel máximo del servidor. ¡Eres una leyenda!", inline=False)
                    
                    await user.send(embed=embed)
                except:
                    pass  # El usuario tiene los DMs cerrados
    
    @commands.command(name="help_levels", aliases=["ayuda_niveles", "niveles_help"])
    async def help_levels(self, ctx):
        """Muestra ayuda completa sobre el sistema de niveles"""
        embed = discord.Embed(
            title="📚 Sistema de Niveles - Guía Completa",
            description="Sistema completo de niveles con ranking, roles automáticos y estadísticas.",
            color=0x00ffff
        )
        
        # Comandos de Usuario
        embed.add_field(
            name="👤 Comandos de Usuario",
            value=(
                "`!perfil [@usuario]` - Ver perfil con imagen personalizada\n"
                "`!xp [@usuario]` - Ver XP actual y progreso\n"
                "`!top [límite] [@usuario]` - Ranking general por XP\n"
                "`!top_semanal [límite]` - Ranking de la semana\n"
                "`!top_mensual [límite]` - Ranking del mes\n"
                "`!insignias [@usuario]` - Ver insignias obtenidas"
            ),
            inline=False
        )
        
        # Comandos de Administrador - Configuración
        embed.add_field(
            name="⚙️ Comandos de Admin - Configuración",
            value=(
                "`!config_canal_nivel [#canal]` - Canal de notificaciones\n"
                "`!config_nivel <nivel> @rol` - Asignar rol a nivel\n"
                "`!config_xp [xp] [cooldown] [mult]` - Configurar parámetros XP\n"
                "`!enable_xp_channel [#canal]` - Habilitar canal para XP\n"
                "`!disable_xp_channel [#canal]` - Deshabilitar canal para XP\n"
                "`!show_config` - Ver configuración actual\n"
                "`!reload_config` - Recargar configuración predefinida"
            ),
            inline=False
        )
        
        # Comandos de Administrador - Gestión
        embed.add_field(
            name="🛠️ Comandos de Admin - Gestión",
            value=(
                "`!set_xp @usuario <cantidad>` - Establecer XP exacta\n"
                "`!add_xp @usuario <cantidad>` - Agregar XP\n"
                "`!set_level @usuario <nivel>` - Establecer nivel exacto\n"
                "`!reset_weekly` - Resetear estadísticas semanales\n"
                "`!reset_monthly` - Resetear estadísticas mensuales\n"
                "`!levels_stats` - Ver estadísticas del servidor"
            ),
            inline=False
        )
        
        # Comandos de Eventos
        embed.add_field(
            name="🎉 Comandos de Eventos",
            value=(
                "`!multiplier_event <mult> <horas>` - Evento XP temporal\n"
                "`!import_levels` - Importar datos (en desarrollo)"
            ),
            inline=False
        )
        
        # Información del Sistema
        embed.add_field(
            name="📊 Información del Sistema",
            value=(
                "**Niveles:** 1-200 (nivel máximo)\n"
                "**XP por mensaje:** Configurable (predeterminado: 15-25)\n"
                "**Cooldown:** 60 segundos entre mensajes\n"
                "**Roles:** Se otorgan cada 10 niveles (10, 20, 30...)\n"
                "**Rankings:** Total, semanal y mensual\n"
                "**Imágenes:** Perfil personalizado con estadísticas"
            ),
            inline=False
        )
        
        # Cómo Funciona
        embed.add_field(
            name="🔄 Cómo Funciona",
            value=(
                "• Envía mensajes para ganar XP automáticamente\n"
                "• Sube de nivel para desbloquear roles especiales\n"
                "• Compite en rankings semanales y mensuales\n"
                "• Obtén insignias por logros especiales\n"
                "• Los administradores pueden configurar todo\n"
                "• Sistema optimizado para 200 niveles máximo"
            ),
            inline=False
        )
        
        embed.set_footer(text="💡 Usa !perfil para ver tu progreso actual | Sistema de Niveles v2.0")
        
        await ctx.send(embed=embed) 

    @commands.command(name="perfill", aliases=["profilee"])
    async def perfill(self, ctx, user: discord.Member = None):
        """Muestra el perfil de un usuario"""
        if user is None:
            user = ctx.author
        
        user_data = await database.get_user_level_data(user.id, ctx.guild.id)
        if not user_data:
            embed = discord.Embed(
                title="❌ Error",
                description="Este usuario no tiene datos registrados.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        # Recalcular nivel por si acaso
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        calculated_level = LevelCalculator.calculate_level(user_data['xp'], guild_config['level_formula'])
        if calculated_level != user_data['level']:
            await database.update_user_level(user.id, ctx.guild.id, calculated_level)
            user_data['level'] = calculated_level
        
        rank = await database.get_user_rank(user.id, ctx.guild.id)
        
        # Generar imagen de perfil
        profile_image = await self.image_generator.generate_profile_image(user, user_data, rank)
        
        if profile_image:
            file = discord.File(profile_image, filename="perfil.png")
            embed = discord.Embed(color=0x00ffff)
            embed.set_image(url="attachment://perfil.png")
            await ctx.send(embed=embed, file=file)
        else:
            # Fallback a embed de texto
            current_level_xp = LevelCalculator.calculate_xp_for_level(user_data['level'])
            next_level_xp = LevelCalculator.calculate_xp_for_level(user_data['level'] + 1)
            progress_xp = user_data['xp'] - current_level_xp
            needed_xp = next_level_xp - current_level_xp
            
            embed = discord.Embed(
                title=f"📊 Perfil de {user.display_name}",
                color=0x00ffff
            )
            embed.add_field(name="Nivel", value=user_data['level'], inline=True)
            embed.add_field(name="Ranking", value=f"#{rank}", inline=True)
            embed.add_field(name="XP Total", value=user_data['xp'], inline=True)
            embed.add_field(name="Progreso", value=f"{progress_xp}/{needed_xp} XP", inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
    
    @commands.command(name="top", aliases=["leaderboard", "ranking"])
    async def top(self, ctx, limit: int = 10, user: discord.Member = None):
        """Muestra el top de usuarios por XP"""
        if user:
            # Mostrar posición específica del usuario
            user_data = await database.get_user_level_data(user.id, ctx.guild.id)
            if not user_data:
                await ctx.send("❌ Este usuario no tiene datos registrados.")
                return
            
            rank = await database.get_user_rank(user.id, ctx.guild.id)
            embed = discord.Embed(
                title=f"📊 Posición de {user.display_name}",
                description=f"**#{rank}** - Nivel {user_data['level']} ({user_data['xp']} XP)",
                color=0x00ffff
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            return
        
        # Mostrar leaderboard general
        leaderboard = await database.get_levels_leaderboard(ctx.guild.id, min(limit, 20))
        
        if not leaderboard:
            await ctx.send("❌ No hay datos de usuarios registrados.")
            return
        
        embed = discord.Embed(
            title="🏆 Top de Usuarios",
            color=0x00ffff
        )
        
        description = ""
        for i, (user_id, xp, level, _, _, _) in enumerate(leaderboard, 1):
            user = ctx.guild.get_member(user_id)
            if user:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                description += f"{medal} {user.display_name} - Nivel {level} ({xp:,} XP)\n"
        
        embed.description = description
        await ctx.send(embed=embed)
    
    @commands.command(name="top_semanal", aliases=["top_weekly"])
    async def top_semanal(self, ctx, limit: int = 10):
        """Muestra el top semanal"""
        leaderboard = await database.get_levels_leaderboard(ctx.guild.id, min(limit, 20), 'weekly')
        
        if not leaderboard:
            await ctx.send("❌ No hay datos semanales registrados.")
            return
        
        embed = discord.Embed(
            title="🏆 Top Semanal",
            color=0x00ff00
        )
        
        description = ""
        for i, (user_id, _, _, weekly_xp, _, _) in enumerate(leaderboard, 1):
            user = ctx.guild.get_member(user_id)
            if user and weekly_xp > 0:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                description += f"{medal} {user.display_name} - {weekly_xp:,} XP esta semana\n"
        
        embed.description = description if description else "No hay actividad esta semana."
        await ctx.send(embed=embed)
    
    @commands.command(name="top_mensual", aliases=["top_monthly"])
    async def top_mensual(self, ctx, limit: int = 10):
        """Muestra el top mensual"""
        leaderboard = await database.get_levels_leaderboard(ctx.guild.id, min(limit, 20), 'monthly')
        
        if not leaderboard:
            await ctx.send("❌ No hay datos mensuales registrados.")
            return
        
        embed = discord.Embed(
            title="🏆 Top Mensual",
            color=0xff6600
        )
        
        description = ""
        for i, (user_id, _, _, monthly_xp, _, _) in enumerate(leaderboard, 1):
            user = ctx.guild.get_member(user_id)
            if user and monthly_xp > 0:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                description += f"{medal} {user.display_name} - {monthly_xp:,} XP este mes\n"
        
        embed.description = description if description else "No hay actividad este mes."
        await ctx.send(embed=embed)
    
    @commands.command(name="xp")
    async def xp(self, ctx, user: discord.Member = None):
        """Muestra la XP actual y progreso de un usuario"""
        if user is None:
            user = ctx.author
        
        user_data = await database.get_user_level_data(user.id, ctx.guild.id)
        if not user_data:
            embed = discord.Embed(
                title="❌ Error",
                description="Este usuario no tiene datos registrados.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        current_level_xp = LevelCalculator.calculate_xp_for_level(user_data['level'], guild_config['level_formula'])
        
        # Verificar si ya está en nivel máximo
        if user_data['level'] >= 200:
            embed = discord.Embed(
                title=f"💎 XP de {user.display_name}",
                color=0xffd700
            )
            embed.add_field(name="Nivel Actual", value="200 (MÁXIMO)", inline=True)
            embed.add_field(name="XP Total", value=f"{user_data['xp']:,}", inline=True)
            embed.add_field(name="Estado", value="🏆 **¡Nivel Máximo Alcanzado!**", inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            await ctx.send(embed=embed)
            return
        
        next_level_xp = LevelCalculator.calculate_xp_for_level(user_data['level'] + 1, guild_config['level_formula'])
        progress_xp = user_data['xp'] - current_level_xp
        needed_xp = next_level_xp - user_data['xp']
        
        # Verificar si el siguiente nivel otorga un rol
        next_role_level = None
        for level in range(user_data['level'] + 1, 201, 10):
            if level % 10 == 0:
                next_role_level = level
                break
        
        embed = discord.Embed(
            title=f"💎 XP de {user.display_name}",
            color=0x00ffff
        )
        embed.add_field(name="Nivel Actual", value=f"{user_data['level']}/200", inline=True)
        embed.add_field(name="XP Total", value=f"{user_data['xp']:,}", inline=True)
        embed.add_field(name="Progreso", value=f"{progress_xp:,}/{next_level_xp - current_level_xp:,}", inline=True)
        embed.add_field(name="Para Siguiente Nivel", value=f"Te faltan **{needed_xp:,} XP** para subir de nivel", inline=False)
        
        if next_role_level:
            embed.add_field(name="🎯 Próximo Rol", value=f"Nivel {next_role_level}", inline=True)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    # Comandos Administrativos
    @commands.command(name="set_xp")
    @commands.has_permissions(administrator=True)
    async def set_xp(self, ctx, user: discord.Member, xp: int):
        """Establece la XP exacta de un usuario"""
        if xp < 0:
            await ctx.send("❌ La XP no puede ser negativa.")
            return
        
        await database.set_user_xp(user.id, ctx.guild.id, xp)
        
        # Recalcular nivel
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        new_level = LevelCalculator.calculate_level(xp, guild_config['level_formula'])
        await database.update_user_level(user.id, ctx.guild.id, new_level)
        
        embed = discord.Embed(
            title="✅ XP Establecida",
            description=f"Se ha establecido la XP de {user.mention} a **{xp:,} XP** (Nivel {new_level})",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="add_xp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, user: discord.Member, xp: int):
        """Agrega XP a un usuario"""
        user_data = await database.get_user_level_data(user.id, ctx.guild.id)
        if not user_data:
            # Crear usuario si no existe
            await database.update_user_xp(user.id, ctx.guild.id, 0)
            user_data = await database.get_user_level_data(user.id, ctx.guild.id)
        
        old_level = user_data['level']
        await database.update_user_xp(user.id, ctx.guild.id, xp)
        
        # Verificar subida de nivel
        updated_data = await database.get_user_level_data(user.id, ctx.guild.id)
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        new_level = LevelCalculator.calculate_level(updated_data['xp'], guild_config['level_formula'])
        
        if new_level != old_level:
            await database.update_user_level(user.id, ctx.guild.id, new_level)
            if new_level > old_level:
                await self.handle_level_up(user, ctx.guild, new_level, guild_config)
        
        embed = discord.Embed(
            title="✅ XP Agregada",
            description=f"Se han agregado **{xp:,} XP** a {user.mention}\nNuevo total: **{updated_data['xp']:,} XP** (Nivel {new_level})",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="set_level")
    @commands.has_permissions(administrator=True)
    async def set_level(self, ctx, user: discord.Member, level: int):
        """Establece el nivel exacto de un usuario"""
        if level < 1 or level > 200:
            await ctx.send("❌ El nivel debe estar entre 1 y 200.")
            return
        
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        required_xp = LevelCalculator.calculate_xp_for_level(level, guild_config['level_formula'])
        
        await database.set_user_xp(user.id, ctx.guild.id, required_xp)
        await database.update_user_level(user.id, ctx.guild.id, level)
        
        embed = discord.Embed(
            title="✅ Nivel Establecido",
            description=f"Se ha establecido el nivel de {user.mention} a **{level}/200** ({required_xp:,} XP)",
            color=0x00ff00
        )
        
        # Mostrar si obtiene un rol
        if level % 10 == 0:
            embed.add_field(name="🎉 Rol Desbloqueado", value=f"Este nivel otorga un rol especial!", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="config_nivel")
    @commands.has_permissions(administrator=True)
    async def config_nivel(self, ctx, level: int, role: discord.Role):
        """Configura un rol para un nivel específico"""
        if level < 1:
            await ctx.send("❌ El nivel debe ser mayor a 0.")
            return
        
        await database.set_level_role(ctx.guild.id, level, role.id)
        
        embed = discord.Embed(
            title="✅ Rol de Nivel Configurado",
            description=f"El rol {role.mention} se otorgará al alcanzar el **nivel {level}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="config_canal_nivel")
    @commands.has_permissions(administrator=True)
    async def config_canal_nivel(self, ctx, channel: discord.TextChannel = None):
        """Configura el canal de notificaciones de subida de nivel"""
        if channel is None:
            channel = ctx.channel
        
        await database.update_guild_config(ctx.guild.id, level_up_channel=channel.id)
        
        embed = discord.Embed(
            title="✅ Canal Configurado",
            description=f"Las notificaciones de subida de nivel se enviarán a {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="config_xp")
    @commands.has_permissions(administrator=True)
    async def config_xp(self, ctx, xp_per_message: int = None, cooldown: int = None, multiplier: float = None):
        """Configura los parámetros de XP del servidor"""
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        
        if xp_per_message is None and cooldown is None and multiplier is None:
            embed = discord.Embed(
                title="⚙️ Configuración Actual de XP",
                color=0x00ffff
            )
            embed.add_field(name="XP por Mensaje", value=guild_config['xp_per_message'], inline=True)
            embed.add_field(name="Cooldown", value=f"{guild_config['xp_cooldown']}s", inline=True)
            embed.add_field(name="Multiplicador", value=f"{guild_config['xp_multiplier']}x", inline=True)
            embed.add_field(name="Fórmula", value=guild_config['level_formula'], inline=True)
            await ctx.send(embed=embed)
            return
        
        # Actualizar valores proporcionados
        update_data = {}
        if xp_per_message is not None:
            update_data['xp_per_message'] = xp_per_message
        if cooldown is not None:
            update_data['xp_cooldown'] = cooldown
        if multiplier is not None:
            update_data['xp_multiplier'] = multiplier
        
        await database.update_guild_config(ctx.guild.id, **update_data)
        
        embed = discord.Embed(
            title="✅ Configuración Actualizada",
            color=0x00ff00
        )
        if xp_per_message is not None:
            embed.add_field(name="XP por Mensaje", value=xp_per_message, inline=True)
        if cooldown is not None:
            embed.add_field(name="Cooldown", value=f"{cooldown}s", inline=True)
        if multiplier is not None:
            embed.add_field(name="Multiplicador", value=f"{multiplier}x", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="enable_xp_channel")
    @commands.has_permissions(administrator=True)
    async def enable_xp_channel(self, ctx, channel: discord.TextChannel = None):
        """Habilita un canal para ganar XP"""
        if channel is None:
            channel = ctx.channel
        
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        enabled_channels = guild_config['enabled_channels']
        
        if channel.id not in enabled_channels:
            enabled_channels.append(channel.id)
            await database.update_guild_config(ctx.guild.id, enabled_channels=enabled_channels)
        
        embed = discord.Embed(
            title="✅ Canal Habilitado",
            description=f"Los usuarios pueden ganar XP en {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="disable_xp_channel")
    @commands.has_permissions(administrator=True)
    async def disable_xp_channel(self, ctx, channel: discord.TextChannel = None):
        """Deshabilita un canal para ganar XP"""
        if channel is None:
            channel = ctx.channel
        
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        disabled_channels = guild_config['disabled_channels']
        
        if channel.id not in disabled_channels:
            disabled_channels.append(channel.id)
            await database.update_guild_config(ctx.guild.id, disabled_channels=disabled_channels)
        
        embed = discord.Embed(
            title="✅ Canal Deshabilitado",
            description=f"Los usuarios NO pueden ganar XP en {channel.mention}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="insignias", aliases=["badges"])
    async def insignias(self, ctx, user: discord.Member = None):
        """Muestra las insignias de un usuario"""
        if user is None:
            user = ctx.author
        
        user_data = await database.get_user_level_data(user.id, ctx.guild.id)
        if not user_data:
            embed = discord.Embed(
                title="❌ Error",
                description="Este usuario no tiene datos registrados.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        badges = user_data['badges'] if user_data['badges'] else []
        
        embed = discord.Embed(
            title=f"🏅 Insignias de {user.display_name}",
            color=0xffd700
        )
        
        if not badges:
            embed.description = "Este usuario no tiene insignias aún."
        else:
            badge_text = ""
            for badge_id in badges:
                # Aquí podrías cargar las insignias desde la base de datos
                badge_text += f"🏅 {badge_id}\n"
            embed.description = badge_text
        
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="reset_weekly")
    @commands.has_permissions(administrator=True)
    async def reset_weekly(self, ctx):
        """Resetea manualmente las estadísticas semanales"""
        await database.reset_weekly_xp(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Estadísticas Semanales Reseteadas",
            description="Se han reseteado todas las estadísticas semanales del servidor.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="reset_monthly")
    @commands.has_permissions(administrator=True)
    async def reset_monthly(self, ctx):
        """Resetea manualmente las estadísticas mensuales"""
        await database.reset_monthly_xp(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Estadísticas Mensuales Reseteadas",
            description="Se han reseteado todas las estadísticas mensuales del servidor.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="multiplier_event")
    @commands.has_permissions(administrator=True)
    async def multiplier_event(self, ctx, multiplier: float, duration_hours: int):
        """Activa un evento de multiplicador de XP temporal"""
        if multiplier <= 0 or duration_hours <= 0:
            await ctx.send("❌ El multiplicador y la duración deben ser positivos.")
            return
        
        # Guardar multiplicador actual
        guild_config = await database.get_guild_level_config(ctx.guild.id)
        original_multiplier = guild_config['xp_multiplier']
        
        # Aplicar nuevo multiplicador
        await database.update_guild_config(ctx.guild.id, xp_multiplier=multiplier)
        
        embed = discord.Embed(
            title="🎉 ¡Evento de XP Activado!",
            description=f"**{multiplier}x XP** activado por **{duration_hours} horas**",
            color=0xff6600
        )
        await ctx.send(embed=embed)
        
        # Programar restauración del multiplicador
        await asyncio.sleep(duration_hours * 3600)  # Convertir horas a segundos
        
        await database.update_guild_config(ctx.guild.id, xp_multiplier=original_multiplier)
        
        # Notificar fin del evento
        embed = discord.Embed(
            title="⏰ Evento de XP Finalizado",
            description=f"El multiplicador de **{multiplier}x XP** ha expirado.",
            color=0x666666
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="import_levels")
    @commands.has_permissions(administrator=True)
    async def import_levels(self, ctx):
        """Comando para importar datos de otros bots de niveles (MEE6, etc.)"""
        embed = discord.Embed(
            title="📥 Importar Niveles",
            description="Esta funcionalidad está en desarrollo.\n\nPronto podrás importar datos de:\n• MEE6\n• Carl-bot\n• Otros bots populares",
            color=0xffaa00
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="levels_stats")
    @commands.has_permissions(administrator=True)
    async def levels_stats(self, ctx):
        """Muestra estadísticas generales del sistema de niveles"""
        stats = await database.get_level_server_stats(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Estadísticas del Sistema de Niveles",
            color=0x00ffff
        )
        embed.add_field(name="Usuarios Registrados", value=f"{stats['total_users']:,}", inline=True)
        embed.add_field(name="Nivel Promedio", value=f"{stats['avg_level']:.1f}", inline=True)
        embed.add_field(name="Mensajes Totales", value=f"{stats['total_messages']:,}", inline=True)
        
        if stats['top_user']:
            top_member = ctx.guild.get_member(stats['top_user'][0])
            if top_member:
                embed.add_field(
                    name="Usuario #1", 
                    value=f"{top_member.display_name}\nNivel {stats['top_user'][2]} ({stats['top_user'][1]:,} XP)", 
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="show_config")
    @commands.has_permissions(administrator=True)
    async def show_config(self, ctx):
        """Muestra la configuración actual del servidor"""
        predefined_config = self.get_predefined_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="⚙️ Configuración del Servidor",
            color=0x00ffff
        )
        
        # Canal de notificaciones
        channel = ctx.guild.get_channel(predefined_config['level_up_channel'])
        channel_name = channel.mention if channel else "❌ No configurado"
        embed.add_field(name="Canal de Notificaciones", value=channel_name, inline=False)
        
        # Configuración de XP
        embed.add_field(name="XP por Mensaje", value=predefined_config['xp_per_message'], inline=True)
        embed.add_field(name="Cooldown", value=f"{predefined_config['xp_cooldown']}s", inline=True)
        embed.add_field(name="Multiplicador", value=f"{predefined_config['xp_multiplier']}x", inline=True)
        embed.add_field(name="Fórmula", value=predefined_config['level_formula'], inline=True)
        
        # Roles por nivel
        level_roles = predefined_config.get('level_roles', {})
        if level_roles:
            roles_text = ""
            for level in sorted(level_roles.keys()):
                role = ctx.guild.get_role(level_roles[level])
                role_name = role.mention if role else f"❌ ID: {level_roles[level]}"
                roles_text += f"**Nivel {level}:** {role_name}\n"
            
            embed.add_field(name="Roles por Nivel", value=roles_text[:1024], inline=False)
        
        # Canales deshabilitados
        if predefined_config['disabled_channels']:
            disabled_text = ""
            for channel_id in predefined_config['disabled_channels']:
                channel = ctx.guild.get_channel(channel_id)
                channel_name = channel.mention if channel else f"❌ ID: {channel_id}"
                disabled_text += f"{channel_name}\n"
            
            embed.add_field(name="Canales Sin XP", value=disabled_text[:1024], inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="reload_config")
    @commands.has_permissions(administrator=True)
    async def reload_config(self, ctx):
        """Recarga la configuración predefinida del código"""
        await self.initialize_guild_configs()
        
        embed = discord.Embed(
            title="✅ Configuración Recargada",
            description="Se ha recargado la configuración predefinida desde el código.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))