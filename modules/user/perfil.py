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
        self.font_path = "resources/fonts"
        self.bg_path = "resources/images/perfil"
    
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
            # Intentar cargar fuentes personalizadas
            font_files = []
            if bold:
                font_files = [
                    'Orbitron-Bold.ttf',
                    'arial-bold.ttf', 
                    'roboto-bold.ttf',
                    'DejaVuSans-Bold.ttf',
                    'NotoSans-Bold.ttf'
                ]
            else:
                font_files = [
                    'Orbitron-Medium.ttf',
                    'Orbitron-Regular.ttf',
                    'arial.ttf',
                    'roboto.ttf', 
                    'DejaVuSans.ttf',
                    'NotoSans-Regular.ttf'
                ]
            
            for font_file in font_files:
                font_path = os.path.join(self.font_path, font_file)
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
                    
        except Exception as e:
            print(f"Error cargando fuente: {e}")
        
        # Fuente por defecto del sistema
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()
    
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
        """Dibuja una barra de progreso redondeada"""
        # Fondo de la barra
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=bg_color
        )
        
        # Barra de progreso
        if progress > 0:
            progress_width = int(width * progress)
            if progress_width > radius:
                draw.rounded_rectangle(
                    [(x, y), (x + progress_width, y + height)],
                    radius=radius,
                    fill=fill_color
                )
    
    def draw_rounded_box(self, draw, x: int, y: int, width: int, height: int, 
                        color: tuple, radius: int = 15):
        """Dibuja una caja redondeada"""
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=color
        )
    
    def draw_outlined_box(self, draw, x: int, y: int, width: int, height: int, 
                         bg_color: tuple, border_color: tuple, radius: int = 15, border_width: int = 3):
        """Dibuja una caja con borde"""
        # Fondo
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=bg_color
        )
        
        # Borde
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            outline=border_color,
            width=border_width
        )
    
    def draw_trophy_icon(self, draw, x: int, y: int, size: int, color: tuple):
        """Dibuja un ícono de trofeo simple"""
        # Base del trofeo
        base_height = 6
        base_y = y + size - base_height
        draw.rectangle([
            (x + size//4, base_y),
            (x + 3*size//4, base_y + base_height)
        ], fill=color)
        
        # Stem
        stem_width = 4
        stem_x = x + size//2 - stem_width//2
        draw.rectangle([
            (stem_x, base_y - 8),
            (stem_x + stem_width, base_y)
        ], fill=color)
        
        # Copa principal
        cup_size = size - 16
        cup_x = x + 8
        cup_y = y + 4
        draw.ellipse([
            (cup_x, cup_y),
            (cup_x + cup_size, cup_y + cup_size - 8)
        ], fill=color)
        
        # Handles
        handle_width = 6
        # Left handle
        draw.arc([
            (cup_x - handle_width, cup_y + 4),
            (cup_x + 4, cup_y + cup_size - 12)
        ], start=270, end=90, fill=color, width=3)
        
        # Right handle
        draw.arc([
            (cup_x + cup_size - 4, cup_y + 4),
            (cup_x + cup_size + handle_width, cup_y + cup_size - 12)
        ], start=90, end=270, fill=color, width=3)
    
    async def create_profile_image(self, user, user_data: dict, guild_config: dict, 
                                 balance: float, rank: int):
        """Crea la imagen del perfil EXACTAMENTE como la imagen de referencia"""
        
        # Dimensiones exactas de la imagen de referencia
        width, height = 600, 750
        
        # Crear imagen base con el fondo exacto
        try:
            background = Image.open(os.path.join(self.bg_path, "perfil.png")).resize((width, height))
        except Exception as e:
            print(f"No se pudo cargar la imagen de fondo: {e}")
            # Fondo azul marino exacto de la imagen
            background = Image.new('RGB', (width, height), (22, 35, 57))
            
        background = background.convert('RGBA')
        draw = ImageDraw.Draw(background)
        
        # Colores EXACTOS de la imagen de referencia
        cyan_bright = (0, 255, 255)      # Cyan brillante para bordes y barra
        cyan_medium = (64, 224, 255)     # Cyan medio para texto
        dark_blue = (28, 45, 75)         # Azul oscuro para cajas
        darker_blue = (20, 32, 55)       # Azul más oscuro para fondos
        white = (255, 255, 255)          # Blanco puro
        trophy_color = (85, 120, 160)    # Color gris-azul para trofeos
        
        # Obtener datos del usuario
        level, current_xp, next_level_xp = self.get_level_from_xp(
            user_data['xp'], guild_config['level_formula']
        )
        
        # Descargar avatar
        avatar = await self.get_user_avatar(user)
        
        # === LAYOUT EXACTO DE LA IMAGEN DE REFERENCIA ===
        
        # 1. AVATAR CIRCULAR (esquina superior izquierda)
        avatar_size = 140
        avatar_x = 40
        avatar_y = 40
        avatar_circular = self.create_circle_avatar(avatar, avatar_size)
        
        # Borde cyan alrededor del avatar (más grueso)
        border_width = 6
        draw.ellipse(
            [(avatar_x - border_width, avatar_y - border_width), 
             (avatar_x + avatar_size + border_width, avatar_y + avatar_size + border_width)],
            outline=cyan_bright,
            width=border_width
        )
        
        background.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)
        
        # Fuentes (tamaños ajustados para coincidir exactamente)
        font_username = self.get_font(42, bold=True)    # Username grande
        font_nivel_label = self.get_font(20, bold=True) # "NIVEL"
        font_nivel_num = self.get_font(32, bold=True)   # Número del nivel
        font_xp = self.get_font(22, bold=True)          # XP numbers
        font_money = self.get_font(36, bold=True)       # Dinero
        font_rank_label = self.get_font(18, bold=True)  # "RANK"
        font_rank_num = self.get_font(28, bold=True)    # Número rank
        
        # 2. USERNAME (a la derecha del avatar)
        username_x = avatar_x + avatar_size + 30
        username_y = avatar_y + 20
        
        # Asegurar que el username sea visible
        username = str(user.display_name)
        if len(username) > 12:
            username = username[:9] + "..."
        
        draw.text((username_x, username_y), username, font=font_username, fill=cyan_medium)
        
        # 3. CAJAS DE NIVEL (debajo del username)
        nivel_y = username_y + 60
        
        # Caja "NIVEL"
        nivel_box_width = 140
        nivel_box_height = 50
        self.draw_rounded_box(draw, username_x, nivel_y, nivel_box_width, nivel_box_height, dark_blue, 12)
        
        # Texto "NIVEL" centrado
        nivel_text = "NIVEL"
        bbox = draw.textbbox((0, 0), nivel_text, font=font_nivel_label)
        text_width = bbox[2] - bbox[0]
        text_x = username_x + (nivel_box_width - text_width) // 2
        text_y = nivel_y + (nivel_box_height - (bbox[3] - bbox[1])) // 2
        draw.text((text_x, text_y), nivel_text, font=font_nivel_label, fill=cyan_medium)
        
        # Caja del número de nivel
        level_box_x = username_x + nivel_box_width + 15
        level_box_width = 80
        self.draw_rounded_box(draw, level_box_x, nivel_y, level_box_width, nivel_box_height, dark_blue, 12)
        
        # Número del nivel centrado
        level_text = str(level)
        bbox = draw.textbbox((0, 0), level_text, font=font_nivel_num)
        text_width = bbox[2] - bbox[0]
        text_x = level_box_x + (level_box_width - text_width) // 2
        text_y = nivel_y + (nivel_box_height - (bbox[3] - bbox[1])) // 2
        draw.text((text_x, text_y), level_text, font=font_nivel_num, fill=white)
        
        # 4. BARRA DE EXPERIENCIA (ancho completo)
        exp_y = avatar_y + avatar_size + 30
        bar_x = 40
        bar_width = width - 80
        bar_height = 30
        
        progress = current_xp / next_level_xp if next_level_xp > 0 else 1.0
        
        self.draw_progress_bar(
            draw, bar_x, exp_y, bar_width, bar_height, progress,
            bg_color=darker_blue,
            fill_color=cyan_bright,
            radius=15
        )
        
        # XP text debajo de la barra
        xp_text = f"{current_xp} / {next_level_xp}"
        draw.text((bar_x, exp_y + bar_height + 15), xp_text, font=font_xp, fill=cyan_medium)
        
        # 5. TROFEOS (3 cajas centradas)
        trophies_y = exp_y + 80
        trophy_size = 90
        trophy_spacing = 25
        
        # Calcular posición para centrar los 3 trofeos
        total_width = (trophy_size * 3) + (trophy_spacing * 2)
        trophies_start_x = (width - total_width) // 2
        
        for i in range(3):
            trophy_x = trophies_start_x + i * (trophy_size + trophy_spacing)
            
            # Caja del trofeo
            self.draw_rounded_box(draw, trophy_x, trophies_y, trophy_size, trophy_size, dark_blue, 15)
            
            # Ícono de trofeo
            icon_size = 50
            icon_x = trophy_x + (trophy_size - icon_size) // 2
            icon_y = trophies_y + (trophy_size - icon_size) // 2
            self.draw_trophy_icon(draw, icon_x, icon_y, icon_size, trophy_color)
        
        # 6. DINERO Y RANK (parte inferior)
        bottom_y = trophies_y + trophy_size + 40
        
        # Caja de dinero (izquierda, con borde cyan)
        money_width = 350
        money_height = 70
        money_x = 40
        
        self.draw_outlined_box(draw, money_x, bottom_y, money_width, money_height,
                              dark_blue, cyan_bright, 15, 4)
        
        # Símbolo € y cantidad
        euro_text = f"€ {int(balance)}"
        
        # Centrar texto en la caja de dinero
        bbox = draw.textbbox((0, 0), euro_text, font=font_money)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = money_x + (money_width - text_width) // 2
        text_y = bottom_y + (money_height - text_height) // 2
        
        draw.text((text_x, text_y), euro_text, font=font_money, fill=cyan_medium)
        
        # Caja de rank (derecha)
        rank_width = 160
        rank_height = 70
        rank_x = money_x + money_width + 50
        
        self.draw_rounded_box(draw, rank_x, bottom_y, rank_width, rank_height, dark_blue, 15)
        
        # "RANK" arriba
        rank_label = "RANK"
        bbox = draw.textbbox((0, 0), rank_label, font=font_rank_label)
        text_width = bbox[2] - bbox[0]
        text_x = rank_x + (rank_width - text_width) // 2
        draw.text((text_x, bottom_y + 12), rank_label, font=font_rank_label, fill=cyan_medium)
        
        # Número de rank abajo
        rank_text = f"#{rank}"
        bbox = draw.textbbox((0, 0), rank_text, font=font_rank_num)
        text_width = bbox[2] - bbox[0]
        text_x = rank_x + (rank_width - text_width) // 2
        draw.text((text_x, bottom_y + 38), rank_text, font=font_rank_num, fill=cyan_medium)
        
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
            profile_img.save(img_buffer, format='PNG', quality=95, optimize=True)
            img_buffer.seek(0)
            
            # Crear archivo de Discord
            file = discord.File(img_buffer, filename=f"perfil_{member.id}.png")
            
            # Enviar imagen
            await ctx.send(file=file)
            
        except Exception as e:
            print(f"Error en comando perfil: {e}")
            import traceback
            print(traceback.format_exc())
            
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
    # Crear directorios necesarios
    os.makedirs("resources/fonts", exist_ok=True)
    os.makedirs("resources/images/perfil", exist_ok=True)
    
    await bot.add_cog(Perfil(bot))