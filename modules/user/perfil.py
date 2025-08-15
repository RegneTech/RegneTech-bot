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
        # Dimensiones de la imagen (más grande para mejor calidad)
        width, height = 900, 500
        
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
        
        # === LAYOUT COMO EN LA IMAGEN ===
        
        # Avatar en la esquina superior izquierda con borde cyan
        avatar_x, avatar_y = 60, 50
        
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
        
        # === INFORMACIÓN DEL USUARIO (DERECHA DEL AVATAR) ===
        
        info_x = avatar_x + avatar_size + 40
        
        # Nombre del usuario (más grande)
        username = user.display_name
        if len(username) > 15:
            username = username[:12] + "..."
        
        draw.text((info_x, avatar_y + 20), username, font=font_huge, fill=white_text)
        
        # Nivel (con estilo cyan)
        level_text = f"NIVEL {level}"
        draw.text((info_x, avatar_y + 80), level_text, font=font_large, fill=cyan_bright)
        
        # === BARRAS DE PROGRESO COMO EN LA IMAGEN ===
        
        progress_y = avatar_y + avatar_size + 40
        
        # Primera barra de progreso (XP) - más larga
        progress = current_xp / next_level_xp if next_level_xp > 0 else 1.0
        
        bar_width = 600
        bar_height = 25
        
        self.draw_progress_bar(
            draw, 60, progress_y, bar_width, bar_height, progress,
            bg_color=darker_blue,
            fill_color=cyan_bright,
            radius=15
        )
        
        # Texto de XP sobre la barra
        xp_text = f"XP: {current_xp:,} / {next_level_xp:,}"
        draw.text((60, progress_y - 30), xp_text, font=font_small, fill=white_text)
        
        # Segunda barra (ejemplo: progreso semanal)
        weekly_progress = min(user_data['weekly_xp'] / 1000, 1.0)  # Ejemplo
        
        self.draw_progress_bar(
            draw, 60, progress_y + 60, bar_width, bar_height, weekly_progress,
            bg_color=darker_blue,
            fill_color=cyan_bright,
            radius=15
        )
        
        # Texto sobre la segunda barra
        draw.text((60, progress_y + 30), f"XP Semanal: {user_data['weekly_xp']:,}", 
                 font=font_small, fill=white_text)
        
        # === CAJAS DE TROFEOS (PARTE INFERIOR) ===
        
        trophies_y = progress_y + 120
        trophy_width = 120
        trophy_height = 80
        trophy_spacing = 150
        
        # Tres cajas de trofeos como en la imagen
        for i in range(3):
            trophy_x = 60 + (i * trophy_spacing)
            
            self.draw_trophy_box(
                draw, trophy_x, trophies_y, trophy_width, trophy_height,
                bg_color=darker_blue,
                border_color=cyan_dark if i != 1 else cyan_bright,  # Destacar el del medio
                radius=15
            )
        
        # === PANEL DE DINERO (IZQUIERDA INFERIOR) ===
        
        money_panel_y = trophies_y + 100
        money_width = 350
        money_height = 60
        
        # Panel de dinero con borde cyan
        draw.rounded_rectangle(
            [(60, money_panel_y), (60 + money_width, money_panel_y + money_height)],
            radius=15,
            fill=darker_blue,
            outline=cyan_bright,
            width=3
        )
        
        # Símbolo de euro y cantidad
        draw.text((80, money_panel_y + 15), f"€ {balance:,.2f}", 
                 font=font_medium, fill=cyan_bright)
        
        # === PANEL DE RANK (DERECHA INFERIOR) ===
        
        rank_x = 60 + money_width + 30
        rank_width = 200
        
        # Panel de rank
        draw.rounded_rectangle(
            [(rank_x, money_panel_y), (rank_x + rank_width, money_panel_y + money_height)],
            radius=15,
            fill=darker_blue,
            outline=cyan_bright,
            width=3
        )
        
        # Texto RANK
        draw.text((rank_x + 20, money_panel_y + 15), f"RANK #{rank}", 
                 font=font_medium, fill=cyan_bright)
        
        # === DETALLES ADICIONALES ===
        
        # Líneas decorativas
        draw.line([(60, progress_y - 10), (width - 60, progress_y - 10)], 
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
            
            # Crear embed básico
            embed = discord.Embed(
                title=f"📊 Perfil de {member.display_name}",
                color=0x00FFFF  # Color cyan
            )
            
            embed.set_image(url=f"attachment://perfil_{member.id}.png")
            embed.set_footer(
                text=f"Solicitado por {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            
            await ctx.send(embed=embed, file=file)
            
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