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
        """Dibuja una barra de progreso"""
        # Fondo de la barra
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=radius,
            fill=bg_color
        )
        
        # Barra de progreso
        if progress > 0:
            progress_width = int(width * progress)
            if progress_width > radius * 2:
                draw.rounded_rectangle(
                    [(x, y), (x + progress_width, y + height)],
                    radius=radius,
                    fill=fill_color
                )
    
    def draw_info_box(self, draw, x: int, y: int, width: int, height: int, 
                     bg_color: tuple, border_color: tuple, radius: int = 15, border_width: int = 3):
        """Dibuja una caja de información con borde"""
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
    
    async def create_profile_image(self, user, user_data: dict, guild_config: dict, 
                                 balance: float, rank: int):
        """Crea la imagen del perfil siguiendo exactamente la imagen de referencia"""
        
        # Dimensiones de la imagen de referencia
        width, height = 600, 800
        
        # Crear imagen base
        try:
            background = Image.open(os.path.join(self.bg_path, "perfil.png")).resize((width, height))
        except Exception as e:
            print(f"No se pudo cargar la imagen de fondo: {e}")
            # Fondo azul oscuro como en la imagen de referencia
            background = Image.new('RGB', (width, height), (16, 31, 56))
            
        background = background.convert('RGBA')
        draw = ImageDraw.Draw(background)
        
        # Colores exactos de la imagen de referencia
        cyan_bright = (0, 255, 255)     # Cyan brillante para bordes y progress bar
        cyan_text = (64, 224, 255)      # Cyan para texto
        dark_bg = (25, 42, 70)          # Fondo oscuro para cajas
        darker_bg = (15, 25, 45)        # Fondo más oscuro
        white_text = (255, 255, 255)    # Texto blanco
        
        # Obtener datos del usuario
        level, current_xp, next_level_xp = self.get_level_from_xp(
            user_data['xp'], guild_config['level_formula']
        )
        
        # Descargar avatar
        avatar = await self.get_user_avatar(user)
        
        # === LAYOUT EXACTO DE LA IMAGEN DE REFERENCIA ===
        
        # Avatar circular en la parte superior izquierda
        avatar_size = 120
        avatar_x = 50
        avatar_y = 50
        avatar_circular = self.create_circle_avatar(avatar, avatar_size)
        
        # Borde cyan alrededor del avatar
        draw.ellipse(
            [(avatar_x - 4, avatar_y - 4), (avatar_x + avatar_size + 4, avatar_y + avatar_size + 4)],
            outline=cyan_bright,
            width=4
        )
        
        background.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)
        
        # Fuentes
        font_username = self.get_font(36, bold=True)  # Nombre de usuario
        font_nivel = self.get_font(24, bold=True)     # "NIVEL"
        font_level_num = self.get_font(32, bold=True) # Número del nivel
        font_xp = self.get_font(20, bold=False)       # XP numbers
        font_money = self.get_font(28, bold=True)     # Dinero
        font_rank = self.get_font(24, bold=True)      # Rank
        
        # === INFORMACIÓN A LA DERECHA DEL AVATAR ===
        
        info_x = avatar_x + avatar_size + 30
        
        # Nombre de usuario (asegurar que sea visible)
        username = str(user.display_name)
        if len(username) > 12:
            username = username[:9] + "..."
            
        # Dibujar el nombre de usuario
        draw.text((info_x, avatar_y + 10), username, font=font_username, fill=cyan_text)
        
        # Cajas de nivel
        nivel_y = avatar_y + 60
        
        # Caja "NIVEL"
        nivel_box_width = 120
        nivel_box_height = 40
        self.draw_info_box(draw, info_x, nivel_y, nivel_box_width, nivel_box_height, 
                          dark_bg, darker_bg, radius=8)
        
        # Texto "NIVEL" centrado en la caja
        nivel_text = "NIVEL"
        bbox = draw.textbbox((0, 0), nivel_text, font=font_nivel)
        text_width = bbox[2] - bbox[0]
        text_x = info_x + (nivel_box_width - text_width) // 2
        text_y = nivel_y + (nivel_box_height - bbox[3] + bbox[1]) // 2
        draw.text((text_x, text_y), nivel_text, font=font_nivel, fill=cyan_text)
        
        # Caja del número de nivel
        level_box_x = info_x + nivel_box_width + 10
        level_box_width = 60
        self.draw_info_box(draw, level_box_x, nivel_y, level_box_width, nivel_box_height,
                          dark_bg, darker_bg, radius=8)
        
        # Número del nivel centrado
        level_text = str(level)
        bbox = draw.textbbox((0, 0), level_text, font=font_level_num)
        text_width = bbox[2] - bbox[0]
        text_x = level_box_x + (level_box_width - text_width) // 2
        text_y = nivel_y + (nivel_box_height - bbox[3] + bbox[1]) // 2
        draw.text((text_x, text_y), level_text, font=font_level_num, fill=white_text)
        
        # === BARRA DE EXPERIENCIA ===
        
        exp_y = avatar_y + avatar_size + 40
        
        # Barra de progreso
        progress = current_xp / next_level_xp if next_level_xp > 0 else 1.0
        bar_width = width - 100
        bar_height = 25
        bar_x = 50
        
        self.draw_progress_bar(
            draw, bar_x, exp_y, bar_width, bar_height, progress,
            bg_color=darker_bg,
            fill_color=cyan_bright,
            radius=12
        )
        
        # Texto de XP debajo de la barra
        xp_text = f"{current_xp} / {next_level_xp}"
        draw.text((bar_x, exp_y + bar_height + 10), xp_text, font=font_xp, fill=cyan_text)
        
        # === TROFEOS (PLACEHOLDER) ===
        
        trophy_y = exp_y + 80
        trophy_size = 80
        trophy_spacing = 20
        
        # Calcular posición para centrar los 3 trofeos
        total_trophies_width = (trophy_size * 3) + (trophy_spacing * 2)
        trophy_start_x = (width - total_trophies_width) // 2
        
        for i in range(3):
            trophy_x = trophy_start_x + i * (trophy_size + trophy_spacing)
            
            # Dibujar caja del trofeo
            self.draw_info_box(draw, trophy_x, trophy_y, trophy_size, trophy_size,
                              dark_bg, darker_bg, radius=12)
            
            # Dibujar símbolo de trofeo simple (rectángulo y líneas)
            trophy_inner_x = trophy_x + 20
            trophy_inner_y = trophy_y + 15
            trophy_inner_size = 40
            
            # Base del trofeo
            draw.rectangle([
                (trophy_inner_x + 10, trophy_inner_y + 30),
                (trophy_inner_x + 30, trophy_inner_y + 35)
            ], fill=(70, 100, 130))
            
            # Copa del trofeo
            draw.ellipse([
                (trophy_inner_x + 5, trophy_inner_y + 10),
                (trophy_inner_x + 35, trophy_inner_y + 30)
            ], fill=(70, 100, 130))
            
            # Asas del trofeo
            draw.arc([
                (trophy_inner_x, trophy_inner_y + 12),
                (trophy_inner_x + 10, trophy_inner_y + 25)
            ], start=270, end=90, fill=(70, 100, 130), width=2)
            
            draw.arc([
                (trophy_inner_x + 30, trophy_inner_y + 12),
                (trophy_inner_x + 40, trophy_inner_y + 25)
            ], start=90, end=270, fill=(70, 100, 130), width=2)
        
        # === DINERO Y RANK ===
        
        bottom_y = trophy_y + trophy_size + 40
        
        # Caja de dinero (más grande, a la izquierda)
        money_width = 300
        money_height = 60
        money_x = 50
        
        self.draw_info_box(draw, money_x, bottom_y, money_width, money_height,
                          dark_bg, cyan_bright, radius=15, border_width=3)
        
        # Símbolo de euro y cantidad
        euro_symbol = "€"
        money_text = f"{euro_symbol} {int(balance)}"
        
        # Centrar el texto en la caja de dinero
        bbox = draw.textbbox((0, 0), money_text, font=font_money)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = money_x + (money_width - text_width) // 2
        text_y = bottom_y + (money_height - text_height) // 2
        
        draw.text((text_x, text_y), money_text, font=font_money, fill=cyan_text)
        
        # Caja de rank (a la derecha)
        rank_width = 150
        rank_height = 60
        rank_x = money_x + money_width + 50
        
        self.draw_info_box(draw, rank_x, bottom_y, rank_width, rank_height,
                          dark_bg, darker_bg, radius=15)
        
        # Texto "RANK" arriba
        rank_label = "RANK"
        bbox = draw.textbbox((0, 0), rank_label, font=font_rank)
        text_width = bbox[2] - bbox[0]
        text_x = rank_x + (rank_width - text_width) // 2
        draw.text((text_x, bottom_y + 5), rank_label, font=font_rank, fill=cyan_text)
        
        # Número de rank abajo
        rank_text = f"#{rank}"
        bbox = draw.textbbox((0, 0), rank_text, font=font_money)
        text_width = bbox[2] - bbox[0]
        text_x = rank_x + (rank_width - text_width) // 2
        draw.text((text_x, bottom_y + 30), rank_text, font=font_money, fill=cyan_text)
        
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