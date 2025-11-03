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
# CUSTOM CSS FOR STYLING
# ============================================

st.markdown("""
    <style>
    div[data-testid="stDataFrame"] th {
        text-align: center !important;
    }
    div[data-testid="stDataFrame"] td {
        text-align: center !important;
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
        st.error(f"Error loading play-by-play data: {e}")
        return None

@st.cache_data(ttl=86400)
def load_roster_data(seasons):
    """Load roster data with player IDs"""
    try:
        rosters = nfl.import_seasonal_rosters(seasons)
        return rosters
    except Exception as e:
        st.error(f"Error loading roster data: {e}")
        return None

# ============================================
# STAT CALCULATION FUNCTIONS
# ============================================

def calculate_qb_stats(pbp, player_name):
    """Calculate QB stats from play-by-play data"""
    qb_plays = pbp[pbp['passer_player_name'] == player_name].copy()
    
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

def calculate_rb_stats(pbp, player_name):
    """Calculate RB stats from play-by-play data"""
    rush_plays = pbp[pbp['rusher_player_name'] == player_name].copy()
    rec_plays = pbp[pbp['receiver_player_name'] == player_name].copy()
    
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

def calculate_wr_te_stats(pbp, player_name):
    """Calculate WR/TE stats from play-by-play data"""
    rec_plays = pbp[pbp['receiver_player_name'] == player_name].copy()
    
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
        'Air Yards': rec_plays['air_yards'].sum(),
        'YAC': rec_plays['yards_after_catch'].sum(),
        'TDs': rec_plays['pass_touchdown'].sum(),
        'First Downs': rec_plays['first_down'].sum()
    }
    
    return stats

# ============================================
# VISUALIZATION FUNCTIONS
# ============================================

def create_comparison_chart(stats_df, metric, title, player_teams):
    """Create a horizontal bar chart with team colors"""
    fig = go.Figure()
    
    stats_sorted = stats_df.sort_values(by=metric, ascending=True)
    
    # Get team colors
    colors = []
    for player in stats_sorted['Player']:
        team = player_teams.get(player, 'NFL')
        color = TEAM_COLORS.get(team, '#1E88E5')  # Default blue if team not found
        colors.append(color)
    
    fig.add_trace(go.Bar(
        x=stats_sorted[metric],
        y=stats_sorted['Player'],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{val:.2f}" for val in stats_sorted[metric]],
        textposition='outside',
        hovertemplate='%{y}<br>%{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=metric,
        yaxis_title="",
        height=max(300, len(stats_df) * 50),
        margin=dict(l=150, r=50, t=50, b=50),
        font=dict(size=12)
    )
    
    return fig

# ============================================
# MAIN APP
# ============================================

def main():
    st.title("🏈 EPA Player Comparison Tool")
    st.markdown("**Compare NFL players using advanced analytics**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        current_year = datetime.now().year
        available_seasons = list(range(2020, current_year + 1))
        season = st.selectbox(
            "Select Season",
            available_seasons,
            index=len(available_seasons) - 1
        )
        
        position = st.selectbox(
            "Select Position",
            ["QB", "RB", "WR", "TE"]
        )
        
        st.markdown("---")
        st.markdown("### 📊 About the Metrics")
        
        if position == "QB":
            st.markdown("""
            **EPA/Play**: Expected Points Added per play  
            **Success Rate**: % of plays with positive EPA  
            **CPOE**: Completion % Over Expected  
            **Air Yards**: Average depth of target  
            """)
        elif position == "RB":
            st.markdown("""
            **Rush EPA/Play**: Expected Points Added per rush  
            **Success Rate**: % of rushes with positive EPA  
            **Rec EPA/Target**: EPA per target as receiver  
            """)
        else:
            st.markdown("""
            **EPA/Target**: Expected Points Added per target  
            **Success Rate**: % of targets with positive EPA  
            **Catch %**: Catch rate on targets  
            **Yards/Target**: Avg yards per target  
            """)
    
    # Load data
    with st.spinner(f"Loading {season} season data..."):
        pbp = load_pbp_data([season])
        rosters = load_roster_data([season])
    
    if pbp is None or rosters is None:
        st.error("Failed to load data. Please try again.")
        return
    
    # DEBUG INFO (temporary)
    with st.sidebar.expander("🔍 DEBUG INFO (click to expand)"):
        st.write("**Available roster columns:**")
        st.write(rosters.columns.tolist())
        if len(rosters) > 0:
            sample = rosters.iloc[0]
            st.write(f"**Sample row:**")
            st.write(f"- player_name: `{sample.get('player_name', 'MISSING')}`")
            st.write(f"- team: `{sample.get('team', 'MISSING')}`")
            st.write(f"- espn_id: `{sample.get('espn_id', 'MISSING')}`")
    
    # Get players by position
    if position == "QB":
        players_in_position = pbp[pbp['passer_player_name'].notna()]['passer_player_name'].unique()
    elif position == "RB":
        rushers = pbp[pbp['rusher_player_name'].notna()]['rusher_player_name'].unique()
        receivers = pbp[pbp['receiver_player_name'].notna()]['receiver_player_name'].unique()
        rb_names = rosters[rosters['position'] == 'RB']['player_name'].unique()
        players_in_position = list(set(rushers) | (set(receivers) & set(rb_names)))
    else:
        players_in_position = pbp[pbp['receiver_player_name'].notna()]['receiver_player_name'].unique()
        position_names = rosters[rosters['position'] == position]['player_name'].unique()
        players_in_position = [p for p in players_in_position if p in position_names]
    
    players_list = sorted(list(players_in_position))
    
    # Player selection
    st.header("👥 Select Players to Compare")
    
    selected_players = st.multiselect(
        "Choose 2-5 players",
        players_list,
        max_selections=5,
        help="Select multiple players to compare their stats"
    )
    
    if len(selected_players) < 2:
        st.info("👆 Please select at least 2 players to compare")
        return
    
    st.markdown("---")
    
    # Calculate stats and gather player info
    all_stats = []
    player_teams = {}
    player_photos = {}
    player_full_names = {}
    
    for player in selected_players:
        # Calculate stats
        if position == "QB":
            stats = calculate_qb_stats(pbp, player)
        elif position == "RB":
            stats = calculate_rb_stats(pbp, player)
        else:
            stats = calculate_wr_te_stats(pbp, player)
        
        if stats:
            # Get player ID from pbp data
            if position == "QB":
                player_plays = pbp[pbp['passer_player_name'] == player]
            elif position == "RB":
                player_plays = pbp[(pbp['rusher_player_name'] == player) | (pbp['receiver_player_name'] == player)]
            else:
                player_plays = pbp[pbp['receiver_player_name'] == player]
            
            if len(player_plays) > 0:
                # Get player ID from first play
                if position == "QB":
                    player_id = player_plays.iloc[0].get('passer_player_id')
                elif position == "RB":
                    player_id = player_plays.iloc[0].get('rusher_player_id')
                    if pd.isna(player_id):
                        player_id = player_plays.iloc[0].get('receiver_player_id')
                else:
                    player_id = player_plays.iloc[0].get('receiver_player_id')
                
                # Match to roster using player_id
                if pd.notna(player_id):
                    player_row = rosters[rosters['player_id'] == player_id]
                    
                    if not player_row.empty:
                        # Get full name
                        first_name = player_row['first_name'].values[0]
                        last_name = player_row['last_name'].values[0]
                        if pd.notna(first_name) and pd.notna(last_name):
                            full_name = f"{first_name} {last_name}"
                        else:
                            full_name = player
                        
                        player_full_names[player] = full_name
                        stats['Player'] = full_name
                        
                        # Get team
                        team = player_row['team'].values[0]
                        player_teams[full_name] = team
                        
                        # Get photo from headshot_url (better than ESPN)
                        headshot = player_row['headshot_url'].values[0]
                        if pd.notna(headshot) and headshot != '':
                            player_photos[full_name] = headshot
                        else:
                            # Fallback to NFL shield
                            player_photos[full_name] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
                        
                        # DEBUG
                        with st.sidebar.expander("🔍 DEBUG INFO (click to expand)"):
                            st.write(f"**{full_name}:** Team=`{team}`, Photo available=`{pd.notna(headshot)}`")
                    else:
                        # No roster match
                        player_full_names[player] = player
                        stats['Player'] = player
                        player_teams[player] = 'NFL'
                        player_photos[player] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
                else:
                    # No player ID
                    player_full_names[player] = player
                    stats['Player'] = player
                    player_teams[player] = 'NFL'
                    player_photos[player] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
            else:
                # No plays found
                player_full_names[player] = player
                stats['Player'] = player
                player_teams[player] = 'NFL'
                player_photos[player] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=150&h=150"
            
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
            team = player_teams[player_name]
            st.caption(f"{team} • {position}")
    
    st.markdown("---")
    
    # ============================================
    # COMPLETE STATISTICS TABLE (MOVED UP!)
    # ============================================
    
    st.header("📋 Complete Statistics")
    
    # Round all numeric columns to 2 decimal places
    display_df = stats_df.copy()
    for col in display_df.columns:
        if col != 'Player' and pd.api.types.is_numeric_dtype(display_df[col]):
            if '%' in col or 'Rate' in col:
                display_df[col] = display_df[col].round(2)
            elif any(x in col for x in ['EPA', 'CPOE', 'Yards', 'YAC']):
                display_df[col] = display_df[col].round(2)
            else:
                display_df[col] = display_df[col].round(0).astype(int)
    
    # Show photos above table
    photo_cols = st.columns(len(all_stats))
    for photo_col, stats_row in zip(photo_cols, all_stats):
        with photo_col:
            player_name = stats_row['Player']
            photo_url = player_photos[player_name]
            st.image(photo_url, width=80)
    
    # Add tooltips to column names
    column_config = {}
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
    # KEY METRICS COMPARISON (MOVED DOWN!)
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
            fig = create_comparison_chart(stats_df, metric, metric_title, player_teams)
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
