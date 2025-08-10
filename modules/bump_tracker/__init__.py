from .bump_tracker import BumpTracker

def setup(bot):
    bot.add_cog(BumpTracker(bot))
