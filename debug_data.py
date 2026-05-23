import sqlite3, pandas as pd

conn = sqlite3.connect('trials.db')
df_trials = pd.read_sql(
    "SELECT nct_id, company, phase, start_year FROM trials WHERE start_year BETWEEN 2015 AND 2025 AND phase IN ('PHASE1','PHASE2','PHASE3')",
    conn)
df_countries = pd.read_sql('SELECT nct_id, country FROM trial_countries', conn)
conn.close()

df = df_trials.merge(df_countries, on='nct_id', how='left')
df['country'] = df['country'].fillna('Unknown')

# Phase 3
phase_df = df[df['phase']=='PHASE3'].copy()
top = phase_df.groupby('country')['nct_id'].nunique().sort_values(ascending=False).head(5)
print('Top 5 countries Phase3:', top.index.tolist())

phase_df['country_group'] = phase_df['country'].apply(lambda c: c if c in top.index else 'Other')
agg = (
    phase_df.drop_duplicates(subset=['nct_id','country_group'])
    .groupby(['start_year','country_group'])['nct_id']
    .count()
    .reset_index(name='count')
)
print('\nUS data:')
print(agg[agg['country_group']=='United States'].to_string())

print('\nPivot:')
pivot = agg.pivot(index='start_year', columns='country_group', values='count')
print(pivot.to_string())
