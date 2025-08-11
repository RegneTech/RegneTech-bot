import discord
from discord.ext import commands
import asyncio
import random
from database import update_user_balance, get_user_balance, add_transaction
from decimal import Decimal

class Sorteos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sorteo_activo = False
        self.canal_sorteo_id = 1404487864204656730
        self.rol_participante_id = 1400106792196898890
        self.participantes_requeridos = 10
        
    def crear_embed_espera(self):
        """Crea el embed de espera para el sorteo"""
        embed = discord.Embed(
            title="🎉 SORTEO ACTIVO - €1.00",
            description=(
                "¡Estás participando en el sorteo por **€1.00**!\n\n"
                "**¿Cómo funciona?**\n"
                "• Necesitas tener el rol de participante\n"
                "• Cuando seamos **10 participantes**, el sorteo comenzará\n"
                "• El ganador recibirá **€1.00** en su balance\n\n"
                f"**Participantes actuales:** Esperando conteo...\n"
                f"**Participantes necesarios:** {self.participantes_requeridos}"
            ),
            color=0x00ff00
        )
        embed.set_footer(text="¡Buena suerte! 🍀")
        return embed
    
    def crear_embed_inicio(self, participantes):
        """Crea el embed cuando el sorteo está por comenzar"""
        embed = discord.Embed(
            title="🚀 ¡SORTEO INICIANDO!",
            description=(
                f"¡Hemos alcanzado **{len(participantes)} participantes**!\n\n"
                "**El sorteo comenzará en 10 minutos** ⏱️\n\n"
                "**Premio:** €1.00 💰\n"
                f"**Participantes:** {len(participantes)}"
            ),
            color=0xffa500
        )
        embed.set_footer(text="¡El ganador se anunciará pronto!")
        return embed
    
    def crear_embed_ganador(self, ganador):
        """Crea el embed del ganador"""
        embed = discord.Embed(
            title="🎉 ¡TENEMOS GANADOR!",
            description=(
                f"**¡Felicidades {ganador.mention}!** 🎊\n\n"
                "**Has ganado €1.00** 💰\n"
                "El dinero ha sido agregado a tu balance.\n\n"
                "**¡La siguiente ronda ya está disponible!**\n"
                "Consigue el rol de participante para unirte."
            ),
            color=0xffd700
        )
        embed.set_footer(text="¡Gracias por participar!")
        return embed

    async def contar_participantes(self, guild):
        """Cuenta los miembros que tienen el rol de participante"""
        rol = guild.get_role(self.rol_participante_id)
        if not rol:
            return []
        return [member for member in rol.members if not member.bot]
    
    async def actualizar_embed_participantes(self, canal):
        """Actualiza el embed con el número actual de participantes"""
        try:
            guild = canal.guild
            participantes = await self.contar_participantes(guild)
            
            embed = discord.Embed(
                title="🎉 SORTEO ACTIVO - €1.00",
                description=(
                    "¡Estás participando en el sorteo por **€1.00**!\n\n"
                    "**¿Cómo funciona?**\n"
                    "• Necesitas tener el rol de participante\n"
                    "• Cuando seamos **10 participantes**, el sorteo comenzará\n"
                    "• El ganador recibirá **€1.00** en su balance\n\n"
                    f"**Participantes actuales:** {len(participantes)}\n"
                    f"**Participantes necesarios:** {self.participantes_requeridos}"
                ),
                color=0x00ff00 if len(participantes) < self.participantes_requeridos else 0xffa500
            )
            embed.set_footer(text="¡Buena suerte! 🍀")
            
            # Buscar el mensaje del embed para actualizarlo
            async for message in canal.history(limit=10):
                if message.author == self.bot.user and message.embeds:
                    if "SORTEO ACTIVO" in message.embeds[0].title:
                        await message.edit(embed=embed)
                        break
                        
            # Verificar si tenemos suficientes participantes
            if len(participantes) >= self.participantes_requeridos and not self.sorteo_activo:
                await self.iniciar_sorteo(canal, participantes)
                
        except Exception as e:
            print(f"Error actualizando embed: {e}")
    
    async def iniciar_sorteo(self, canal, participantes):
        """Inicia el proceso del sorteo"""
        if self.sorteo_activo:
            return
            
        self.sorteo_activo = True
        
        try:
            # Limpiar canal
            await canal.purge(limit=100)
            
            # Enviar embed de inicio
            rol = canal.guild.get_role(self.rol_participante_id)
            embed_inicio = self.crear_embed_inicio(participantes)
            
            await canal.send(
                content=f"🎉 {rol.mention} ¡EL SORTEO ESTÁ POR COMENZAR!",
                embed=embed_inicio
            )
            
            # Esperar 10 minutos (600 segundos)
            await asyncio.sleep(600)
            
            # Elegir ganador aleatorio
            ganador = random.choice(participantes)
            
            # Agregar dinero al ganador
            saldo_actual = await get_user_balance(ganador.id)
            nuevo_saldo = saldo_actual + Decimal('1.00')
            await update_user_balance(
                ganador.id, 
                nuevo_saldo, 
                self.bot.user.id, 
                'PREMIO_SORTEO', 
                'Premio por ganar sorteo de €1.00'
            )
            
            # Registrar transacción
            await add_transaction(
                ganador.id, 
                'PREMIO', 
                1.00, 
                'Ganador del sorteo - €1.00'
            )
            
            # Quitar rol a todos los participantes
            for participante in participantes:
                try:
                    await participante.remove_roles(rol, reason="Fin del sorteo")
                except:
                    continue
            
            # Limpiar canal nuevamente
            await canal.purge(limit=100)
            
            # Anunciar ganador con mención al rol
            embed_ganador = self.crear_embed_ganador(ganador)
            await canal.send(
                content=f"🎉 {rol.mention} ¡EL SORTEO HA TERMINADO!\n\n🏆 **GANADOR:** {ganador.mention}\n💰 **Se han añadido €1.00 a tu cuenta!**",
                embed=embed_ganador
            )
            
            # Esperar 5 minutos antes de limpiar y empezar nueva ronda
            await asyncio.sleep(300)  # 300 segundos = 5 minutos
            await canal.purge(limit=100)
            
            # Enviar embed para nueva ronda
            embed_nueva_ronda = self.crear_embed_espera()
            await canal.send(embed=embed_nueva_ronda)
            
        except Exception as e:
            print(f"Error en sorteo: {e}")
        finally:
            self.sorteo_activo = False

    @commands.command(name="sorteo_setup")
    @commands.has_permissions(administrator=True)
    async def sorteo_setup(self, ctx):
        """Configura el sorteo en el canal específico"""
        if ctx.channel.id != self.canal_sorteo_id:
            await ctx.send("❌ Este comando solo se puede usar en el canal de sorteos.")
            return
            
        # Limpiar canal
        await ctx.channel.purge(limit=100)
        
        # Enviar embed inicial
        embed = self.crear_embed_espera()
        await ctx.send(embed=embed)
        
        print(f"✅ Sorteo configurado en el canal {ctx.channel.name}")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Detecta cuando alguien obtiene o pierde el rol de participante"""
        if self.sorteo_activo:
            return
            
        canal = self.bot.get_channel(self.canal_sorteo_id)
        if not canal:
            return
            
        # Verificar si cambió el rol de participante
        rol_antes = self.rol_participante_id in [r.id for r in before.roles]
        rol_despues = self.rol_participante_id in [r.id for r in after.roles]
        
        if rol_antes != rol_despues:
            # Actualizar embed con nuevo conteo
            await asyncio.sleep(1)  # Pequeña pausa para asegurar que el cambio se procesó
            await self.actualizar_embed_participantes(canal)

    @commands.command(name="sorteo_test")
    @commands.has_permissions(administrator=True)
    async def sorteo_test(self, ctx):
        """Comando de prueba para administradores"""
        embed = discord.Embed(
            title="✅ Módulo Sorteos funcionando",
            description="El módulo de sorteos está cargado correctamente.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
        
    @commands.command(name="sorteo_info")
    @commands.has_permissions(administrator=True)
    async def sorteo_info(self, ctx):
        """Muestra información del sistema de sorteos"""
        canal = self.bot.get_channel(self.canal_sorteo_id)
        rol = ctx.guild.get_role(self.rol_participante_id)
        participantes = await self.contar_participantes(ctx.guild)
        
        embed = discord.Embed(
            title="🎲 Información del Sistema de Sorteos",
            color=0x3498db
        )
        embed.add_field(
            name="📍 Canal de Sorteos", 
            value=canal.mention if canal else "❌ No encontrado",
            inline=False
        )
        embed.add_field(
            name="🎭 Rol de Participante", 
            value=rol.mention if rol else "❌ No encontrado",
            inline=False
        )
        embed.add_field(
            name="👥 Participantes Actuales", 
            value=f"{len(participantes)}/{self.participantes_requeridos}",
            inline=True
        )
        embed.add_field(
            name="🎮 Estado", 
            value="🟢 Activo" if self.sorteo_activo else "🟡 En espera",
            inline=True
        )
        embed.add_field(
            name="💰 Premio", 
            value="€1.00",
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="force_sorteo")
    @commands.has_permissions(administrator=True)
    async def force_sorteo(self, ctx):
        """Fuerza el inicio de un sorteo (solo para testing)"""
        if ctx.channel.id != self.canal_sorteo_id:
            await ctx.send("❌ Este comando solo se puede usar en el canal de sorteos.")
            return
            
        participantes = await self.contar_participantes(ctx.guild)
        
        if len(participantes) < 2:
            await ctx.send("❌ Se necesitan al menos 2 participantes para forzar un sorteo.")
            return
            
        await ctx.send("🚀 Forzando inicio del sorteo...")
        await self.iniciar_sorteo(ctx.channel, participantes)

async def setup(bot: commands.Bot):
    await bot.add_cog(Sorteos(bot))