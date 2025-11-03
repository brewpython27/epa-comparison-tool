"""
EPA Player Comparison Tool  
Built with love for exploring advanced NFL stats
"""

import streamlit as st
import pandas as pd
import numpy as np
import nfl_data_py as nfl
import plotly.graph_objects as go
import requests
from datetime import datetime

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="EPA Player Comparison",
    page_icon="🏈",
    layout="wide"
)

# ============================================
# NFL TEAM COLORS (for charts)
# ============================================

TEAM_COLORS = {
    'ARI': '#97233F', 'ATL': '#A71930', 'BAL': '#241773', 'BUF': '#00338D',
    'CAR': '#0085CA', 'CHI': '#C83803', 'CIN': '#FB4F14', 'CLE': '#311D00',
    'DAL': '#041E42', 'DEN': '#FB4F14', 'DET': '#0076B6', 'GB': '#203731',
    'HOU': '#03202F', 'IND': '#002C5F', 'JAX': '#006778', 'KC': '#E31837',
    'LAC': '#0080C6', 'LAR': '#003594', 'LV': '#000000', 'MIA': '#008E97',
    'MIN': '#4F2683', 'NE': '#002244', 'NO': '#D3BC8D', 'NYG': '#0B2265',
    'NYJ': '#125740', 'PHI': '#004C54', 'PIT': '#FFB612', 'SEA': '#002244',
    'SF': '#AA0000', 'TB': '#D50A0A', 'TEN': '#0C2340', 'WAS': '#5A1414'
}

# ============================================
# STAT DEFINITIONS (for tooltips)
# ============================================

STAT_DEFINITIONS = {
    'EPA/Play': 'Expected Points Added per play - measures how much value a player adds',
    'Success Rate': 'Percentage of plays with positive EPA',
    'CPOE': 'Completion Percentage Over Expected - accuracy vs difficulty of throws',
    'Air Yards/Att': 'Average depth of target downfield',
    'YAC/Comp': 'Yards After Catch per completion',
    'Pass TDs': 'Passing touchdowns',
    'INTs': 'Interceptions thrown',
    'Sacks': 'Times sacked',
    'Comp %': 'Completion percentage',
    'Rush EPA/Play': 'Expected Points Added per rushing attempt',
    'Rush Success Rate': 'Percentage of rushes with positive EPA',
    'Rec EPA/Target': 'Expected Points Added per target as a receiver',
    'Rush TDs': 'Rushing touchdowns',
    'EPA/Target': 'Expected Points Added per target',
    'Catch %': 'Percentage of targets caught',
    'Yards/Target': 'Average yards per target',
    'Plays': 'Total number of plays',
    'Targets': 'Number of times targeted',
    'Receptions': 'Number of catches',
    'Yards': 'Total yards gained',
    'TDs': 'Touchdowns scored',
    'First Downs': 'First downs gained',
    'Rush Attempts': 'Number of rushing attempts',
    'Rush Yards': 'Rushing yards gained',
    'Rec Yards': 'Receiving yards gained',
    'Rec TDs': 'Receiving touchdowns',
    'Air Yards': 'Total air yards (depth of targets)',
    'YAC': 'Total yards after catch'
}

# ============================================
# REFERENCE LINES FOR CONTEXT
# ============================================

REFERENCE_LINES = {
    'QB': {
        'EPA/Play': 0.10,
        'Success Rate': 43,
        'Comp %': 64
    },
    'RB': {
        'Rush EPA/Play': 0.02,
        'Rush Success Rate': 42,
        'Rec EPA/Target': 0.15
    },
    'WR': {
        'EPA/Target': 0.18,
        'Success Rate': 48,
        'Catch %': 63,
        'Yards/Target': 8.0
    },
    'TE': {
        'EPA/Target': 0.15,
        'Success Rate': 48,
        'Catch %': 63,
        'Yards/Target': 7.5
    }
}

# ============================================
# CUSTOM CSS FOR STYLING
# ============================================

st.markdown("""
    <style>
    /* Target every possible table element */
    div[data-testid="stDataFrame"] table,
    div[data-testid="stDataFrame"] table * {
        text-align: center !important;
    }
    
    div[data-testid="stDataFrame"] th,
    div[data-testid="stDataFrame"] td {
        text-align: center !important;
        vertical-align: middle !important;
        padding: 8px !important;
    }
    
    /* Target the cell wrapper divs */
    div[data-testid="stDataFrame"] [data-testid="stDataFrameCell"],
    div[data-testid="stDataFrame"] [data-testid="stDataFrameCell"] > div {
        text-align: center !important;
        justify-content: center !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Target column headers specifically */
    div[data-testid="stDataFrame"] [data-testid="stDataFrameColHeader"],
    div[data-testid="stDataFrame"] [data-testid="stDataFrameColHeader"] > div {
        text-align: center !important;
        justify-content: center !important;
    }
    
    /* Make photo column narrow */
    div[data-testid="stDataFrame"] th:first-child,
    div[data-testid="stDataFrame"] td:first-child {
        width: 80px !important;
        min-width: 80px !important;
        max-width: 80px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# DATA LOADING FUNCTIONS
# ============================================

@st.cache_data(ttl=86400)
def load_pbp_data(seasons):
    """Load play-by-play data from nflfastR"""
    try:
        pbp = nfl.import_pbp_data(seasons)
        return pbp
    except Exception as e:
        st.error(f"Error loading play-by-play data: {str(e)}")
        return None

@st.cache_data(ttl=86400)
def load_roster_data(seasons):
    """Load roster data with player IDs"""
    try:
        rosters = nfl.import_seasonal_rosters(seasons)
        return rosters
    except Exception as e:
        st.error(f"Error loading roster data: {str(e)}")
        return None

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_player_display_name(abbreviated_name, team, pbp, rosters, position):
    """Get display name in 'LastName, FirstName (TEAM)' format"""
    try:
        # Get player ID from pbp - filtering by both name and team
        if position == "QB":
            player_plays = pbp[(pbp['passer_player_name'] == abbreviated_name) & 
                              (pbp['posteam'] == team)]
            if len(player_plays) > 0:
                player_id = player_plays.iloc[0].get('passer_player_id')
        elif position == "RB":
            player_plays = pbp[((pbp['rusher_player_name'] == abbreviated_name) | 
                              (pbp['receiver_player_name'] == abbreviated_name)) & 
                              (pbp['posteam'] == team)]
            if len(player_plays) > 0:
                player_id = player_plays.iloc[0].get('rusher_player_id')
                if pd.isna(player_id):
                    player_id = player_plays.iloc[0].get('receiver_player_id')
        else:
            player_plays = pbp[(pbp['receiver_player_name'] == abbreviated_name) & 
                              (pbp['posteam'] == team)]
            if len(player_plays) > 0:
                player_id = player_plays.iloc[0].get('receiver_player_id')
        
        if pd.notna(player_id):
            player_row = rosters[rosters['player_id'] == player_id]
            if not player_row.empty:
                last_name = player_row['last_name'].values[0]
                
                # Try football_name first (jersey name - usually first name)
                football_name = player_row['football_name'].values[0]
                if pd.notna(football_name) and football_name.strip():
                    first_name = football_name
                else:
                    # Fallback to regular first_name
                    first_name = player_row['first_name'].values[0]
                
                if pd.notna(last_name) and pd.notna(first_name):
                    return f"{last_name}, {first_name} ({team})"
    except:
        pass
    
    return f"{abbreviated_name} ({team})"

# ============================================
# STAT CALCULATION FUNCTIONS
# ============================================

def calculate_qb_stats(pbp, player_name, team):
    """Calculate QB stats from play-by-play data"""
    qb_plays = pbp[(pbp['passer_player_name'] == player_name) & 
                   (pbp['posteam'] == team)].copy()
    
    if len(qb_plays) == 0:
        return None
    
    stats = {
        'Player': player_name,
        'Plays': len(qb_plays),
        'EPA/Play': qb_plays['epa'].mean(),
        'Success Rate': (qb_plays['success'].sum() / len(qb_plays) * 100),
        'CPOE': qb_plays['cpoe'].mean(),
        'Air Yards/Att': qb_plays['air_yards'].mean(),
        'YAC/Comp': qb_plays[qb_plays['complete_pass'] == 1]['yards_after_catch'].mean(),
        'Pass TDs': qb_plays['pass_touchdown'].sum(),
        'INTs': qb_plays['interception'].sum(),
        'Sacks': qb_plays['sack'].sum(),
        'Comp %': (qb_plays['complete_pass'].sum() / len(qb_plays) * 100)
    }
    
    return stats

def calculate_rb_stats(pbp, player_name, team):
    """Calculate RB stats from play-by-play data"""
    rush_plays = pbp[(pbp['rusher_player_name'] == player_name) & 
                     (pbp['posteam'] == team)].copy()
    rec_plays = pbp[(pbp['receiver_player_name'] == player_name) & 
                    (pbp['posteam'] == team)].copy()
    
    if len(rush_plays) == 0 and len(rec_plays) == 0:
        return None
    
    stats = {
        'Player': player_name,
        'Rush Attempts': len(rush_plays),
        'Rush EPA/Play': rush_plays['epa'].mean() if len(rush_plays) > 0 else 0,
        'Rush Success Rate': (rush_plays['success'].sum() / len(rush_plays) * 100) if len(rush_plays) > 0 else 0,
        'Rush Yards': rush_plays['yards_gained'].sum(),
        'Rush TDs': rush_plays['rush_touchdown'].sum(),
        'Targets': len(rec_plays),
        'Rec EPA/Target': rec_plays['epa'].mean() if len(rec_plays) > 0 else 0,
        'Receptions': rec_plays['complete_pass'].sum(),
        'Rec Yards': rec_plays['yards_gained'].sum(),
        'Rec TDs': rec_plays['pass_touchdown'].sum()
    }
    
    return stats

def calculate_wr_te_stats(pbp, player_name, team):
    """Calculate WR/TE stats from play-by-play data"""
    rec_plays = pbp[(pbp['receiver_player_name'] == player_name) & 
                    (pbp['posteam'] == team)].copy()
    
    if len(rec_plays) == 0:
        return None
    
    stats = {
        'Player': player_name,
        'Targets': len(rec_plays),
        'EPA/Target': rec_plays['epa'].mean(),
        'Success Rate': (rec_plays['success'].sum() / len(rec_plays) * 100),
        'Receptions': rec_plays['complete_pass'].sum(),
        'Catch %': (rec_plays['complete_pass'].sum() / len(rec_plays) * 100),
        'Yards': rec_plays['yards_gained'].sum(),
        'Yards/Target': rec_plays['yards_gained'].mean(),
        'TDs': rec_plays['pass_touchdown'].sum(),
        'First Downs': rec_plays['first_down'].sum(),
        'Air Yards': rec_plays['air_yards'].sum(),
        'YAC': rec_plays['yards_after_catch'].sum()
    }
    
    return stats

# ============================================
# CHART CREATION FUNCTION
# ============================================

def create_comparison_chart(stats_df, metric, metric_title, player_teams, position):
    """Create horizontal bar chart for player comparison"""
    
    # Sort data
    stats_sorted = stats_df.sort_values(by=metric, ascending=True).copy()
    
    # Get colors based on player teams
    colors = [TEAM_COLORS.get(player_teams.get(player, 'NFL'), '#808080') 
              for player in stats_sorted['Player']]
    
    # Create figure
    fig = go.Figure()
    
    # Add bar trace
    fig.add_trace(go.Bar(
        x=stats_sorted[metric],
        y=stats_sorted['Player'],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{val:.2f}" for val in stats_sorted[metric]],
        textposition='inside',
        textfont=dict(color='white', size=12),
        insidetextanchor='start',
        hovertemplate='%{y}<br>%{text}<extra></extra>'
    ))
    
    # Add reference line if available (skip CPOE since 0 is the baseline)
    if metric != 'CPOE' and position in REFERENCE_LINES and metric in REFERENCE_LINES[position]:
        avg_value = REFERENCE_LINES[position][metric]
        fig.add_vline(
            x=avg_value,
            line_dash="dash",
            line_color="gray",
            line_width=2,
            opacity=0.6,
            annotation_text="League Avg",
            annotation_position="top",
            annotation=dict(font_size=10, font_color="gray")
        )
    
    # Calculate height based on number of players
    height = min(450, max(300, len(stats_sorted) * 75))
    
    # Update layout
    fig.update_layout(
        title=metric_title,
        xaxis_title=metric,
        yaxis_title="",
        showlegend=False,
        height=height,
        margin=dict(l=20, r=20, t=20, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# ============================================
# MAIN APPLICATION
# ============================================

def main():
    # Header
    st.title("🏈 EPA Player Comparison Tool")
    st.markdown("**Compare NFL players using advanced analytics**")
    st.markdown("---")
    
    # Sidebar for selections
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Season selection
        current_year = datetime.now().year
        available_seasons = list(range(2020, current_year + 1))
        season = st.selectbox(
            "Select Season",
            available_seasons,
            index=len(available_seasons) - 1
        )
        
        # Position selection
        position = st.selectbox(
            "Select Position",
            ["QB", "RB", "WR", "TE"]
        )
        
        # Week selector
        st.markdown("---")
        week_options = ["All"] + list(range(1, 19))
        selected_weeks = st.selectbox(
            "Select Week(s)",
            week_options,
            index=0,
            help="Filter data by specific week or view all weeks"
        )
        
        # Multi-week range option
        if selected_weeks != "All":
            use_range = st.checkbox("Select week range?")
            if use_range:
                week_end = st.selectbox(
                    "Through week:",
                    list(range(selected_weeks, 19)),
                    help="End week for range"
                )
            else:
                week_end = selected_weeks
                use_range = False
        else:
            week_end = None
            use_range = False
        
        st.markdown("---")
        st.markdown("### 📊 About the Metrics")
        
        if position == "QB":
            st.markdown("""
            EPA/Play: Expected Points Added per play  
            Success Rate: % of plays with positive EPA  
            CPOE: Completion % Over Expected  
            Air Yards: Average depth of target  
            """)
        elif position == "RB":
            st.markdown("""
            Rush EPA/Play: Expected Points Added per rush  
            Success Rate: % of rushes with positive EPA  
            Rec EPA/Target: EPA per target as receiver  
            """)
        else:
            st.markdown("""
            EPA/Target: Expected Points Added per target  
            Success Rate: % of targets with positive EPA  
            Catch %: Catch rate on targets  
            Yards/Target: Avg yards per target  
            """)
    
    # Load data
    with st.spinner(f"Loading {season} season data..."):
        pbp = load_pbp_data([season])
        rosters = load_roster_data([season])
    
    if pbp is None or rosters is None:
        st.error("Failed to load data. Please try again.")
        return
    
    # Filter by weeks if selected
    if selected_weeks != "All":
        if use_range and week_end:
            pbp = pbp[pbp['week'].between(selected_weeks, week_end)]
            st.info(f"📅 Showing weeks {selected_weeks}-{week_end}")
        else:
            pbp = pbp[pbp['week'] == selected_weeks]
            st.info(f"📅 Showing week {selected_weeks} only")
    
    # Get players with team info to handle duplicates
    player_team_pairs = []
    
    if position == "QB":
        qb_data = pbp[pbp['passer_player_name'].notna()][['passer_player_name', 'posteam']].drop_duplicates()
        player_team_pairs = [(row['passer_player_name'], row['posteam']) for _, row in qb_data.iterrows()]
        
    elif position == "RB":
        rush_data = pbp[pbp['rusher_player_name'].notna()][['rusher_player_name', 'posteam']].drop_duplicates()
        rec_data = pbp[pbp['receiver_player_name'].notna()][['receiver_player_name', 'posteam']].drop_duplicates()
        
        rushers = [(row['rusher_player_name'], row['posteam']) for _, row in rush_data.iterrows()]
        receivers = [(row['receiver_player_name'], row['posteam']) for _, row in rec_data.iterrows()]
        
        player_team_pairs = list(set(rushers + receivers))
        
    else:  # WR or TE
        rec_data = pbp[pbp['receiver_player_name'].notna()][['receiver_player_name', 'posteam']].drop_duplicates()
        player_team_pairs = [(row['receiver_player_name'], row['posteam']) for _, row in rec_data.iterrows()]
    
    # Filter by roster position
    position_rosters = rosters[rosters['position'] == position]
    valid_player_ids = set(position_rosters['player_id'].dropna())
    
    # Filter to only include correct position
    filtered_player_team_pairs = []
    for player_abbrev, team in player_team_pairs:
        # Get player_id to verify position
        if position == "QB":
            player_plays = pbp[(pbp['passer_player_name'] == player_abbrev) & (pbp['posteam'] == team)]
            if len(player_plays) > 0:
                player_id = player_plays.iloc[0].get('passer_player_id')
        elif position == "RB":
            player_plays = pbp[((pbp['rusher_player_name'] == player_abbrev) | 
                              (pbp['receiver_player_name'] == player_abbrev)) & 
                              (pbp['posteam'] == team)]
            if len(player_plays) > 0:
                player_id = player_plays.iloc[0].get('rusher_player_id')
                if pd.isna(player_id):
                    player_id = player_plays.iloc[0].get('receiver_player_id')
        else:
            player_plays = pbp[(pbp['receiver_player_name'] == player_abbrev) & (pbp['posteam'] == team)]
            if len(player_plays) > 0:
                player_id = player_plays.iloc[0].get('receiver_player_id')
        
        if pd.notna(player_id) and player_id in valid_player_ids:
            filtered_player_team_pairs.append((player_abbrev, team))
    
    if not filtered_player_team_pairs:
        st.warning(f"No {position} players found for the selected season/week(s)")
        return
    
    # Create mapping from (abbreviated_name, team) to display name
    name_mapping = {}
    for player_abbrev, team in filtered_player_team_pairs:
        display_name = get_player_display_name(player_abbrev, team, pbp, rosters, position)
        key = f"{player_abbrev}|{team}"
        name_mapping[key] = display_name
    
    # Create dropdown options (reversed: display_name -> key)
    dropdown_options = {display_name: key for key, display_name in name_mapping.items()}
    display_names_sorted = sorted(dropdown_options.keys())
    
    # Player selection
    st.header("👥 Select Players to Compare")
    
    selected_display_names = st.multiselect(
        "Choose 2-5 players",
        display_names_sorted,
        max_selections=5,
        help="Select multiple players to compare their stats"
    )
    
    if len(selected_display_names) < 2:
        st.info("👆 Please select at least 2 players to compare")
        return
    
    # Convert display names back to (abbreviated_name, team) tuples for stats calculation
    selected_players = []
    for display_name in selected_display_names:
        key = dropdown_options[display_name]
        player_abbrev, team = key.split('|')
        selected_players.append((player_abbrev, team))
    
    st.markdown("---")
    
    # Calculate stats and gather player info
    all_stats = []
    player_teams = {}
    player_photos = {}
    
    for player_abbrev, team in selected_players:
        # Calculate stats
        if position == "QB":
            stats = calculate_qb_stats(pbp, player_abbrev, team)
        elif position == "RB":
            stats = calculate_rb_stats(pbp, player_abbrev, team)
        else:
            stats = calculate_wr_te_stats(pbp, player_abbrev, team)
        
        if stats:
            # Get display name and update stats
            display_name = get_player_display_name(player_abbrev, team, pbp, rosters, position)
            stats['Player'] = display_name
            
            # Store team for colors
            player_teams[display_name] = team
            
            # Get player ID for photo
            if position == "QB":
                player_plays = pbp[(pbp['passer_player_name'] == player_abbrev) & (pbp['posteam'] == team)]
                if len(player_plays) > 0:
                    player_id = player_plays.iloc[0].get('passer_player_id')
            elif position == "RB":
                player_plays = pbp[((pbp['rusher_player_name'] == player_abbrev) | 
                                  (pbp['receiver_player_name'] == player_abbrev)) & 
                                  (pbp['posteam'] == team)]
                if len(player_plays) > 0:
                    player_id = player_plays.iloc[0].get('rusher_player_id')
                    if pd.isna(player_id):
                        player_id = player_plays.iloc[0].get('receiver_player_id')
            else:
                player_plays = pbp[(pbp['receiver_player_name'] == player_abbrev) & (pbp['posteam'] == team)]
                if len(player_plays) > 0:
                    player_id = player_plays.iloc[0].get('receiver_player_id')
            
            # Get photo from roster
            if pd.notna(player_id):
                player_row = rosters[rosters['player_id'] == player_id]
                if not player_row.empty:
                    headshot = player_row['headshot_url'].values[0]
                    if pd.notna(headshot) and headshot != '':
                        player_photos[display_name] = headshot
                    else:
                        player_photos[display_name] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
                else:
                    player_photos[display_name] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
            else:
                player_photos[display_name] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
            
            all_stats.append(stats)
    
    if not all_stats:
        st.warning("No stats found for selected players")
        return
    
    stats_df = pd.DataFrame(all_stats)
    
    # ============================================
    # PLAYER OVERVIEW WITH PHOTOS
    # ============================================
    
    st.header("📸 Player Overview")
    
    cols = st.columns(len(all_stats))
    
    for col, stats_row in zip(cols, all_stats):
        with col:
            player_name = stats_row['Player']
            photo_url = player_photos[player_name]
            st.image(photo_url, width=150)
            st.markdown(f"**{player_name}**")
            st.caption(f"{position}")
    
    st.markdown("---")
    
    # ============================================
    # COMPLETE STATISTICS TABLE
    # ============================================
    
    st.header("📋 Complete Statistics")
    
    # Round all numeric columns
    display_df = stats_df.copy()
    
    for col in display_df.columns:
        if col != 'Player' and pd.api.types.is_numeric_dtype(display_df[col]):
            if '%' in col or 'Rate' in col:
                display_df[col] = display_df[col].round(2)
            elif any(x in col for x in ['EPA', 'CPOE', 'Yards', 'YAC']):
                display_df[col] = display_df[col].round(2)
            else:
                display_df[col] = display_df[col].round(0).astype(int)
    
    # Add Photo column
    photo_urls = []
    for stats_row in all_stats:
        player_name = stats_row['Player']
        photo_urls.append(player_photos[player_name])
    
    display_df.insert(0, '📷', photo_urls)
    
    # Configure columns
    column_config = {
        '📷': st.column_config.ImageColumn(
            "📷",
            width="small"
        )
    }
    
    for col in display_df.columns:
        if col in STAT_DEFINITIONS:
            column_config[col] = st.column_config.Column(
                col,
                help=STAT_DEFINITIONS[col]
            )
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )
    
    st.markdown("---")
    
    # ============================================
    # KEY METRICS COMPARISON
    # ============================================
    
    st.header("📊 Key Metrics Comparison")
    
    if position == "QB":
        key_metrics = ['EPA/Play', 'Success Rate', 'CPOE', 'Comp %']
    elif position == "RB":
        key_metrics = ['Rush EPA/Play', 'Rush Success Rate', 'Rec EPA/Target', 'Rush TDs']
    else:
        key_metrics = ['EPA/Target', 'Success Rate', 'Catch %', 'Yards/Target']
    
    for metric in key_metrics:
        if metric in stats_df.columns:
            # Add tooltip from definitions
            metric_title = f"{metric}"
            if metric in STAT_DEFINITIONS:
                metric_title += f" - {STAT_DEFINITIONS[metric]}"
            
            st.subheader(metric)
            
            # Create chart
            fig = create_comparison_chart(stats_df, metric, metric_title, player_teams, position)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Download button
    csv = stats_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Comparison as CSV",
        data=csv,
        file_name=f"epa_comparison_{position}_{season}.csv",
        mime="text/csv"
    )
    
    # Footer
    st.markdown("---")
    st.caption("Data source: nflfastR • Built with ❤️ using Streamlit")

if __name__ == "__main__":
    main()
