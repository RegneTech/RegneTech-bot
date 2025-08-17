import discord
from discord.ext import commands
import asyncio
from datetime import datetime

class Partner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="partner")
    async def partner_command(self, ctx):
        """Comando para crear un nuevo partner"""
        
        # Verificar que sea el canal correcto
        if ctx.channel.id != 1406342012017573908:
            return
        
        # Verificar que tenga el rol correcto
        required_role_id = 1406343428085911582
        if not any(role.id == required_role_id for role in ctx.author.roles):
            await ctx.send("❌ No tienes permisos para usar este comando.")
            return
        
        # Solicitar contenido del partner
        await ctx.send("📝 A continuación escribe el contenido del partner:")
        
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel
        
        try:
            # Esperar respuesta del usuario (30 segundos de timeout)
            content_message = await self.bot.wait_for('message', check=check, timeout=30.0)
            content = content_message.content
            
            # Verificar que no esté vacío
            if not content.strip():
                await ctx.send("❌ El contenido no puede estar vacío.")
                return
            
            # Importar funciones de database.py
            from database import get_next_partner_number, save_partner
            
            # Obtener número de partner
            partner_number = await get_next_partner_number()
            
            # Guardar en base de datos
            await save_partner(ctx.author.id, ctx.author.display_name, content)
            
            # Canal donde enviar el partner
            target_channel = self.bot.get_channel(1400106793811705858)
            if not target_channel:
                await ctx.send("❌ No se pudo encontrar el canal de destino.")
                return
            
            # Crear mensaje del partner
            partner_message = f"**Partner #{partner_number}**\nRealizado por: {ctx.author.display_name}\n\n{content}"
            
            # Enviar al canal de partners
            await target_channel.send(partner_message)
            
            # Confirmar al usuario
            await ctx.send(f"✅ Partner #{partner_number} enviado correctamente.")
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Tiempo agotado. Inténtalo de nuevo.")
        except Exception as e:
            await ctx.send(f"❌ Ocurrió un error: {str(e)}")

    @commands.command(name="partner_stats")
    @commands.has_permissions(administrator=True)
    async def partner_stats(self, ctx):
        """Muestra estadísticas de partners (solo administradores)"""
        from database import get_partner_stats
        
        stats = await get_partner_stats()
        
        embed = discord.Embed(
            title="📊 Estadísticas de Partners",
            color=0x3498db
        )
        embed.add_field(name="Total de Partners", value=str(stats['total']), inline=False)
        
        if stats['top_users']:
            top_list = "\n".join([f"{name}: {count} partners" for name, count in stats['top_users']])
            embed.add_field(name="Top Usuarios", value=top_list, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="partner_list")
    @commands.has_permissions(administrator=True)
    async def partner_list(self, ctx, limit: int = 5):
        """Lista los últimos partners (solo administradores)"""
        from database import get_partners_list
        
        partners = await get_partners_list(limit)
        
        if not partners:
            await ctx.send("No hay partners registrados.")
            return
        
        embed = discord.Embed(
            title=f"📋 Últimos {len(partners)} Partners",
            color=0x9b59b6
        )
        
        for partner_id, author, content, created_at in partners:
            # Limitar contenido mostrado
            short_content = content[:100] + "..." if len(content) > 100 else content
            embed.add_field(
                name=f"Partner #{partner_id} - {author}",
                value=f"{short_content}\n*{created_at}*",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="partner_delete")
    @commands.has_permissions(administrator=True)
    async def partner_delete(self, ctx, partner_id: int):
        """Elimina un partner por ID (solo administradores)"""
        from database import delete_partner
        
        success = await delete_partner(partner_id)
        
        if success:
            await ctx.send(f"✅ Partner #{partner_id} eliminado correctamente.")
        else:
            await ctx.send(f"❌ No se encontró el partner #{partner_id}")

    @commands.command(name="partner_test")
    @commands.has_permissions(administrator=True)
    async def partner_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Partner funcionando",
            description="El módulo de partner está cargado correctamente.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Partner(bot))