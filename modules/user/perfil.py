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
        self.font_path = "resources\fonts"  # Carpeta donde están las fuentes
        self.bg_path = "resources\images\perfil\perfil.png"  # Carpeta donde están los fondos
    
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
                # Buscar archivos de fuente bold en la carpeta fonts
                font_files = ['bold.ttf', 'arial-bold.ttf', 'roboto-bold.ttf', 'font-bold.ttf']
                for font_file in font_files:
                    try:
                        return ImageFont.truetype(f"{self.font_path}{font_file}", size)
                    except:
                        continue
            else:
                # Buscar archivos de fuente regular en la carpeta fonts
                font_files = ['regular.ttf', 'arial.ttf', 'roboto.ttf', 'font.ttf']
                for font_file in font_files:
                    try:
                        return ImageFont.truetype(f"{self.font_path}{font_file}", size)
                    except:
                        continue
        except:
            pass
        
        # Fuente por defecto si no encuentra ninguna personalizada
        return ImageFont.load_default()
    
    def create_rounded_rectangle(self, width: int, height: int, radius: int, color: tuple):
        """Crea un rectángulo con esquinas redondeadas"""
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Dibujar el rectángulo redondeado
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
                         progress: float, bg_color: tuple, fill_color: tuple, radius: int = 10):
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
    
    async def create_profile_image(self, user, user_data: dict, guild_config: dict, 
                                 balance: float, rank: int):
        """Crea la imagen del perfil"""
        # Dimensiones de la imagen
        width, height = 800, 400
        
        # Crear imagen base
        try:
            # Intentar cargar fondo personalizado
            background = Image.open(f"{self.bg_path}profile_bg.png").resize((width, height))
        except:
            # Fondo degradado por defecto
            background = Image.new('RGB', (width, height), (47, 49, 54))
            
        # Crear overlay semi-transparente
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 100))
        background = background.convert('RGBA')
        background = Image.alpha_composite(background, overlay)
        
        draw = ImageDraw.Draw(background)
        
        # Obtener datos del usuario
        level, current_xp, next_level_xp = self.get_level_from_xp(
            user_data['xp'], guild_config['level_formula']
        )
        
        # Descargar y procesar avatar
        avatar = await self.get_user_avatar(user)
        avatar_circular = self.create_circle_avatar(avatar, 120)
        
        # Posicionar avatar
        avatar_x, avatar_y = 50, 50
        background.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)
        
        # Fuentes
        font_large = self.get_font(32, bold=True)
        font_medium = self.get_font(24)
        font_small = self.get_font(18)
        font_tiny = self.get_font(14)
        
        # Colores
        text_color = (10, 231, 255)  # #0AE7FF
        accent_color = (10, 231, 255)  # #0AE7FF para barra de progreso
        success_color = (67, 181, 129)  # Verde para dinero
        warning_color = (250, 166, 26)  # Naranja para rank
        
        # === INFORMACIÓN DEL USUARIO ===
        
        # Nombre del usuario
        username = user.display_name
        if len(username) > 20:
            username = username[:17] + "..."
        
        draw.text((200, 60), username, font=font_large, fill=text_color)
        
        # Nivel actual
        level_text = f"Nivel {level}"
        draw.text((200, 100), level_text, font=font_medium, fill=accent_color)
        
        # === BARRA DE PROGRESO DE XP ===
        
        progress = current_xp / next_level_xp if next_level_xp > 0 else 1.0
        
        # Texto de XP
        xp_text = f"{current_xp:,} / {next_level_xp:,} XP"
        draw.text((200, 140), xp_text, font=font_small, fill=text_color)
        
        # Barra de progreso
        self.draw_progress_bar(
            draw, 200, 170, 300, 20, progress,
            bg_color=(60, 60, 60, 180),
            fill_color=accent_color,
            radius=10
        )
        
        # Porcentaje
        percentage_text = f"{progress * 100:.1f}%"
        draw.text((520, 165), percentage_text, font=font_tiny, fill=text_color)
        
        # === ESTADÍSTICAS ===
        
        stats_y = 220
        
        # XP Total
        total_xp_text = f"XP Total: {user_data['xp']:,}"
        draw.text((50, stats_y), total_xp_text, font=font_small, fill=text_color)
        
        # Dinero
        money_text = f"💰 Dinero: ${balance:,.2f}"
        draw.text((50, stats_y + 30), money_text, font=font_small, fill=success_color)
        
        # Ranking
        rank_text = f"🏆 Rank: #{rank}"
        draw.text((50, stats_y + 60), rank_text, font=font_small, fill=warning_color)
        
        # === ESTADÍSTICAS ADICIONALES (LADO DERECHO) ===
        
        # XP Semanal
        weekly_xp_text = f"XP Semanal: {user_data['weekly_xp']:,}"
        draw.text((400, stats_y), weekly_xp_text, font=font_small, fill=text_color)
        
        # XP Mensual
        monthly_xp_text = f"XP Mensual: {user_data['monthly_xp']:,}"
        draw.text((400, stats_y + 30), monthly_xp_text, font=font_small, fill=text_color)
        
        # === DECORACIONES ===
        
        # Marco alrededor del avatar
        draw.ellipse(
            [(avatar_x - 3, avatar_y - 3), (avatar_x + 123, avatar_y + 123)],
            outline=accent_color,
            width=3
        )
        
        # Línea separadora
        draw.line([(50, 210), (750, 210)], fill=(10, 231, 255, 100), width=2)
        
        return background
    
    @commands.command(name="perfillll", aliases=["profileee", "p"])
    @commands.cooldown(1, 30, commands.BucketType.user)  # Cooldown de 30 segundos
    async def perfillll(self, ctx, member: discord.Member = None):
        """Muestra el perfil de un usuario con imagen personalizada"""
        
        # Si no se especifica miembro, usar el autor del comando
        if member is None:
            member = ctx.author
        
        # Verificar que no sea un bot
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
            profile_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Crear archivo de Discord
            file = discord.File(img_buffer, filename=f"perfil_{member.id}.png")
            
            # Crear embed básico
            embed = discord.Embed(
                title=f"📊 Perfil de {member.display_name}",
                color=0x7289da
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
    
    @perfillll.error
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
    os.makedirs("fonts", exist_ok=True)
    os.makedirs("assets/backgrounds", exist_ok=True)
    
    await bot.add_cog(Perfil(bot))