import discord
from discord.ext import commands
from discord import app_commands
from discord.ext import tasks
import sqlite3

TOKEN = "YOUR_TOKEN_HERE"



intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="$",
    intents=intents
)

conn = sqlite3.connect("awards.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS awards (
    user_id INTEGER,
    username TEXT,
    ribbon TEXT,
    awarded_by TEXT
)
""")
conn.commit()


# ---------------- DATABASE HELPERS ----------------

def add_award(user: discord.Member, ribbon: str, awarded_by: discord.User):
    cursor.execute(
        "INSERT INTO awards VALUES (?, ?, ?, ?)",
        (user.id, str(user), ribbon, str(awarded_by))
    )
    conn.commit()


def get_user_ribbons(user_id: int):
    cursor.execute(
        "SELECT ribbon FROM awards WHERE user_id=?",
        (user_id,)
    )
    return cursor.fetchall()


def get_ribbon_users(ribbon: str):
    cursor.execute(
        "SELECT username FROM awards WHERE ribbon=?",
        (ribbon,)
    )
    return cursor.fetchall()


def get_ribbon_stats():
    cursor.execute("""
        SELECT ribbon, COUNT(*)
        FROM awards
        GROUP BY ribbon
    """)
    return cursor.fetchall()


# ---------------- EVENTS ----------------

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")

    print(f"Logged in as {bot.user}")

# ---------------- Ribbons ----------------

RIBBONS = {
    "Valuable Vanguard": "Top overall performance in the Squad",
    "Rained the Pain": "Most Stratgems in the Squad",
    "Scientist-in-Training": "Highest Sample Yield in the Squad",
    "Deadshot Accuracy": "Highest Accuracy in the Squad",
    "Blind": "Worst accuracy in the Squad",
    "Friendliest Foe": "Most friendly fire in the Squad",
    "Forrest Gump": "Ran the furthest in the Squad",
    "Road Rage": "Flipped any FRV or Bastion variant",
    "Kaboom?": "Used the Hellbomb Backback",
    "Yes Rico, kaboom": "Activated another Vanguard's Hellbomb Backpack",
    "Saint's Family": "Most deaths in the Squad"
}


# ---------------- COMMANDS ----------------

    await ctx.send(embed=embed)

@bot.tree.command(
    name="help",
    description="Shows all available bot commands"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="Ribbon Bot Commands",
        description="List of available commands",
    )

    embed.add_field(
        name="/award",
        value="Award a ribbon to a user",
        inline=False
    )

    embed.add_field(
        name="/stack",
        value="View all ribbons earned by a user",
        inline=False
    )

    embed.add_field(
        name="/lookup_ribbon",
        value="Find users with a specific ribbon",
        inline=False
    )

    embed.add_field(
        name="/lookup_distribution",
        value="View ribbon statistics",
        inline=False
    )

    embed.add_field(
        name="/list_ribbons",
        value="Display all available ribbons",
        inline=False
    )

    embed.add_field(
        name="/remove_ribbon",
        value="Remove one ribbon from a user (Admin only)",
        inline=False
    )

    embed.add_field(
        name="/clear_user_awards",
        value="Remove all ribbons from one user (Admin only)",
        inline=False
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="remove_ribbon",
    description="Remove a specific ribbon from a user"
)
@app_commands.describe(member="User to remove a ribbon from",
                       ribbon="Ribbon to remove"
)
@app_commands.choices(
    ribbon=[
        app_commands.Choice(name=name, value=name)
        for name in RIBBONS.keys()
    ]
)
async def remove_ribbon(
    interaction: discord.Interaction,
    member: discord.Member,
    ribbon: app_commands.Choice[str]
):

    # Admin-only
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to do this.",
            ephemeral=True
        )
        return

    ribbon_name = ribbon.value

    # Check if user has that ribbon
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM awards
        WHERE user_id=? AND ribbon=?
        """,
        (member.id, ribbon_name)
    )

    count = cursor.fetchone()[0]

    if count == 0:
        await interaction.response.send_message(
            f"{member.display_name} does not have **{ribbon_name}**.",
            ephemeral=True
        )
        return

    # Remove ONE occurrence only
    cursor.execute(
        """
        DELETE FROM awards
        WHERE rowid = (
            SELECT rowid
            FROM awards
            WHERE user_id=? AND ribbon=?
            LIMIT 1
        )
        """,
        (member.id, ribbon_name)
    )

    conn.commit()

    embed = discord.Embed(
        title="Ribbon Removed",
        description=(
            f"Removed "
            f"{ribbon_name}** "
            f"from {member.mention}"
        )
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="clear_user_awards",
    description="Remove all ribbons from a specific user"
)
@app_commands.describe(
    member="User whose ribbons should be removed"
)
async def clear_user_awards(
    interaction: discord.Interaction,
    member: discord.Member
):

    # Admin-only protection
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to do this.",
            ephemeral=True
        )
        return

    # Count ribbons first
    cursor.execute(
        "SELECT COUNT(*) FROM awards WHERE user_id=?",
        (member.id,)
    )

    count = cursor.fetchone()[0]

    if count == 0:
        await interaction.response.send_message(
            f"{member.display_name} has no ribbons.",
            ephemeral=True
        )
        return

    # Delete only that user's ribbons
    cursor.execute(
        "DELETE FROM awards WHERE user_id=?",
        (member.id,)
    )

    conn.commit()

    embed = discord.Embed(
        title="Ribbons Cleared",
        description=f"Removed **{count}** ribbon(s) from {member.mention}"
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clear_all_awards", description="Delete ALL awarded ribbons (admin only)")
async def clear_all_awards(interaction: discord.Interaction):

    # Permission check (VERY important)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You do not have permission to do this.",
            ephemeral=True
        )
        return

    cursor.execute("DELETE FROM awards")
    conn.commit()

    embed = discord.Embed(
        title="⚠️ All Awards Cleared",
        description="Every ribbon has been removed from the database."
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_ribbons", description="Show all available ribbons")
async def list_ribbons(interaction: discord.Interaction):

    text = "\n".join(
        f" **{name}** — {desc}"
        for name, desc in RIBBONS.items()
    )

    embed = discord.Embed(
        title="Available Ribbons",
        description=text
    )

    await interaction.response.send_message(embed=embed)


from discord import app_commands

RIBBON_CHOICES = [
    app_commands.Choice(name=name, value=name)
    for name in RIBBONS.keys()
]


@bot.tree.command(name="award", description="Award a ribbon")
@app_commands.describe(
    member="User to award",
    ribbon="Choose a valid ribbon"
)
@app_commands.choices(ribbon=RIBBON_CHOICES)
async def award(
    interaction: discord.Interaction,
    member: discord.Member,
    ribbon: app_commands.Choice[str]
):

    ribbon_name = ribbon.value

    add_award(member, ribbon_name, interaction.user)

    embed = discord.Embed(
        title="Ribbon Awarded",
        description=f"{member.mention} received **{[ribbon_name]} {ribbon_name}**"
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="stack", description="View user ribbon stack")
async def stack(interaction: discord.Interaction, member: discord.Member):
    ribbons = get_user_ribbons(member.id)

    if not ribbons:
        await interaction.response.send_message(
            f"{member.display_name} has no ribbons."
        )
        return

    ribbon_list = "\n".join(f"🏅 {r[0]}" for r in ribbons)

    embed = discord.Embed(
        title=f"{member.display_name}'s Stack",
        description=ribbon_list
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="lookup_ribbon", description="Find users with ribbon")
async def lookup_ribbon(interaction: discord.Interaction, ribbon: str):
    users = get_ribbon_users(ribbon)

    if not users:
        await interaction.response.send_message("Nobody has this ribbon.")
        return

    names = "\n".join(set(u[0] for u in users))

    await interaction.response.send_message(
        f"Users with **{ribbon}**:\n{names}"
    )


@bot.tree.command(name="lookup_distribution", description="Ribbon statistics")
async def lookup_distribution(interaction: discord.Interaction):
    data = get_ribbon_stats()

    if not data:
        await interaction.response.send_message("No awards exist.")
        return

    text = "\n".join(f"{r}: {c}" for r, c in data)

    embed = discord.Embed(
        title="Ribbon Distribution",
        description=text
    )

    await interaction.response.send_message(embed=embed)


# ---------------- RUN BOT ----------------

bot.run(TOKEN)
