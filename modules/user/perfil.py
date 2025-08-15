import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
from database import (
    get_user_level_data, 
    get_user_balance, 
    get_user_rank,
    get_guild_level_config
)
import math

class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_path = "resources/fonts"  # Cambio: usar / en lugar de \
        self.bg_path = "resources/images/perfil"  # Cambio: usar / en lugar de \
    
    def calculate_level_xp(self, level: int, formula: str = 'exponential') -> int:
        """Calcula la XP necesaria para un nivel específico"""
        if formula == 'linear':
            return level * 100
        elif formula == 'quadratic':
            return level * level * 50
        else:  # exponential (default)
            return int(100 * (1.2 ** (level - 1)))
    
    def calculate_total_xp_for_level(self, level: int, formula: str = 'exponential') -> int:
        """Calcula la XP total necesaria para alcanzar un nivel"""
        total = 0
        for i in range(1, level):
            total += self.calculate_level_xp(i, formula)
        return total
    
    def get_level_from_xp(self, xp: int, formula: str = 'exponential') -> tuple:
        """Obtiene el nivel actual y XP necesaria para el siguiente nivel"""
        level = 1
        total_xp_used = 0
        
        while True:
            xp_needed = self.calculate_level_xp(level, formula)
            if total_xp_used + xp_needed > xp:
                break
            total_xp_used += xp_needed
            level += 1
        
        current_level_xp = xp - total_xp_used
        next_level_xp = self.calculate_level_xp(level, formula)
        
        return level, current_level_xp, next_level_xp
    
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
            if bold:
                font_files = ['bold.ttf', 'arial-bold.ttf', 'roboto-bold.ttf', 'font-bold.ttf']
                for font_file in font_files:
                    try:
                        return ImageFont.truetype(f"{self.font_path}/{font_file}", size)  # Cambio: agregar /
                    except:
                        continue
            else:
                font_files = ['regular.ttf', 'arial.ttf', 'roboto.ttf', 'font.ttf']
                for font_file in font_files:
                    try:
                        return ImageFont.truetype(f"{self.font_path}/{font_file}", size)  # Cambio: agregar /
                    except:
                        continue
        except:
            pass
        
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
    
    def draw_trophy_box(self, draw, x: int, y: int, width: int, height: int, 
                       bg_color: tuple, border_color: tuple, radius: int = 15):
        """Dibuja una caja de trofeo como en la imagen"""
        # Fondo de la caja
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=bg_color
        )
        
        # Borde cyan
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            outline=border_color,
            width=2
        )
        
        # Simular trofeo con texto (sin emoji por compatibilidad)
        font = self.get_font(30, bold=True)
        draw.text((x + width//2 - 15, y + height//2 - 20), "🏆", 
                 font=font, fill=border_color)
    
    async def create_profile_image(self, user, user_data: dict, guild_config: dict, 
                                 balance: float, rank: int):
        """Crea la imagen del perfil con el diseño exacto de la imagen"""
        # Dimensiones 3:4 como solicitado
        width, height = 600, 800
        
        # Crear imagen base con fondo azul oscuro como en la imagen
        try:
            # Intentar cargar fondo personalizado
            background = Image.open(f"{self.bg_path}/perfil.png").resize((width, height))  # Cambio: agregar /
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
        
        # Obtener datos del usuario
        level, current_xp, next_level_xp = self.get_level_from_xp(
            user_data['xp'], guild_config['level_formula']
        )
        
        # Descargar y procesar avatar (más grande)
        avatar = await self.get_user_avatar(user)
        avatar_size = 140
        avatar_circular = self.create_circle_avatar(avatar, avatar_size)
        
        # === LAYOUT ADAPTADO PARA FORMATO 3:4 ===
        
        # Avatar en la parte superior centrado
        avatar_x = (width - avatar_size) // 2
        avatar_y = 40
        
        # Borde cyan alrededor del avatar
        draw.ellipse(
            [(avatar_x - 5, avatar_y - 5), (avatar_x + avatar_size + 5, avatar_y + avatar_size + 5)],
            outline=cyan_bright,
            width=4
        )
        
        background.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)
        
        # Fuentes más grandes
        font_huge = self.get_font(42, bold=True)    # Para el nombre
        font_large = self.get_font(28, bold=True)   # Para nivel
        font_medium = self.get_font(22, bold=True)  # Para textos importantes
        font_small = self.get_font(18)              # Para detalles
        
        # === INFORMACIÓN DEL USUARIO (DEBAJO DEL AVATAR) ===
        
        info_y = avatar_y + avatar_size + 30
        
        # Nombre del usuario centrado
        username = user.display_name
        if len(username) > 15:
            username = username[:12] + "..."
        
        # Calcular posición centrada para el texto
        bbox = draw.textbbox((0, 0), username, font=font_huge)
        text_width = bbox[2] - bbox[0]
        username_x = (width - text_width) // 2
        
        draw.text((username_x, info_y), username, font=font_huge, fill=white_text)
        
        # Nivel centrado
        level_text = f"NIVEL {level}"
        bbox = draw.textbbox((0, 0), level_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        level_x = (width - text_width) // 2
        
        draw.text((level_x, info_y + 60), level_text, font=font_large, fill=cyan_bright)
        
        # === BARRAS DE PROGRESO CENTRADAS ===
        
        progress_y = info_y + 140
        
        # Primera barra de progreso (XP) - adaptada al ancho
        progress = current_xp / next_level_xp if next_level_xp > 0 else 1.0
        
        bar_width = width - 80  # Margen de 40px a cada lado
        bar_height = 30
        bar_x = 40
        
        self.draw_progress_bar(
            draw, bar_x, progress_y, bar_width, bar_height, progress,
            bg_color=darker_blue,
            fill_color=cyan_bright,
            radius=15
        )
        
        # Texto de XP centrado sobre la barra
        xp_text = f"XP: {current_xp:,} / {next_level_xp:,}"
        bbox = draw.textbbox((0, 0), xp_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        xp_x = (width - text_width) // 2
        draw.text((xp_x, progress_y - 30), xp_text, font=font_small, fill=white_text)
        
        # Segunda barra (ejemplo: progreso semanal)
        weekly_progress = min(user_data['weekly_xp'] / 1000, 1.0)
        
        self.draw_progress_bar(
            draw, bar_x, progress_y + 80, bar_width, bar_height, weekly_progress,
            bg_color=darker_blue,
            fill_color=cyan_bright,
            radius=15
        )
        
        # Texto centrado sobre la segunda barra
        weekly_text = f"XP Semanal: {user_data['weekly_xp']:,}"
        bbox = draw.textbbox((0, 0), weekly_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        weekly_x = (width - text_width) // 2
        draw.text((weekly_x, progress_y + 50), weekly_text, font=font_small, fill=white_text)
        
        # === CAJAS DE TROFEOS CENTRADAS ===
        
        trophies_y = progress_y + 160
        trophy_width = 120
        trophy_height = 80
        
        # Calcular espaciado para centrar las 3 cajas
        total_trophies_width = 3 * trophy_width
        available_space = width - total_trophies_width
        trophy_spacing = available_space // 4  # Espacios: inicio, entre1, entre2, final
        
        # Tres cajas de trofeos centradas
        for i in range(3):
            trophy_x = trophy_spacing + (i * (trophy_width + trophy_spacing))
            
            self.draw_trophy_box(
                draw, trophy_x, trophies_y, trophy_width, trophy_height,
                bg_color=darker_blue,
                border_color=cyan_dark if i != 1 else cyan_bright,  # Destacar el del medio
                radius=15
            )
        
        # === PANELES INFERIORES APILADOS VERTICALMENTE ===
        
        panels_y = trophies_y + 120
        panel_width = width - 80  # Margen de 40px a cada lado
        panel_height = 60
        panel_x = 40
        
        # Panel de dinero
        draw.rounded_rectangle(
            [(panel_x, panels_y), (panel_x + panel_width, panels_y + panel_height)],
            radius=15,
            fill=darker_blue,
            outline=cyan_bright,
            width=3
        )
        
        # Símbolo de euro y cantidad centrado
        money_text = f"€ {balance:,.2f}"
        bbox = draw.textbbox((0, 0), money_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        money_x = (width - text_width) // 2
        draw.text((money_x, panels_y + 15), money_text, font=font_medium, fill=cyan_bright)
        
        # Panel de rank (debajo del de dinero)
        rank_y = panels_y + panel_height + 20
        
        draw.rounded_rectangle(
            [(panel_x, rank_y), (panel_x + panel_width, rank_y + panel_height)],
            radius=15,
            fill=darker_blue,
            outline=cyan_bright,
            width=3
        )
        
        # Texto RANK centrado
        rank_text = f"RANK #{rank}"
        bbox = draw.textbbox((0, 0), rank_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        rank_x = (width - text_width) // 2
        draw.text((rank_x, rank_y + 15), rank_text, font=font_medium, fill=cyan_bright)
        
        # === DETALLES ADICIONALES ===
        
        # Líneas decorativas centradas
        line_margin = 60
        draw.line([(line_margin, progress_y - 10), (width - line_margin, progress_y - 10)], 
                 fill=cyan_dark, width=2)
        
        return background
    
    @commands.command(name="perfil", aliases=["profile", "p"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def perfil(self, ctx, member: discord.Member = None):
        """Muestra el perfil de un usuario con imagen personalizada"""
        
        if member is None:
            member = ctx.author
        
        if member.bot:
            embed = discord.Embed(
                title="❌ Error",
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
                    title="❌ Usuario no encontrado",
                    description=f"{member.mention} no tiene datos registrados en el sistema de niveles.",
                    color=0xff0000
                )
                await ctx.send(embed=embed)
                return
            
            # Obtener configuración del servidor
            guild_config = await get_guild_level_config(ctx.guild.id)
            
            # Obtener balance del usuario
            balance = await get_user_balance(member.id)
            
            # Obtener ranking del usuario
            rank = await get_user_rank(member.id, ctx.guild.id)
            
            # Crear imagen del perfil
            profile_img = await self.create_profile_image(
                member, user_data, guild_config, float(balance), rank
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
                title="❌ Error",
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

async def setup(bot: commands.Bot):
    # Crear directorios necesarios con las rutas corregidas
    os.makedirs("resources/fonts", exist_ok=True)
    os.makedirs("resources/images/perfil", exist_ok=True)
    
    await bot.add_cog(Perfil(bot))