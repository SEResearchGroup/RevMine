import sys, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analyze_service.settings')
django.setup()

from io import StringIO
from unittest.mock import MagicMock
import pandas as pd
from analytics.domain.metrics.metrics_engine import MetricsEngine

INLINE_CSV = """\
Project_ID,MR_ID,Creation_Date,Lead_Time,#Discussions,#Commits,Mean_Time_between_commits,Commiters,#UniqueCommiters,nb_minor_author,nb_major_author,delta_time,churn_addition,churn_deletions,initial_mr_size,hist_entropy,modified_files,filetypes,state,rework_size,#people,#reviewers,#commiters,#discussionners,additions,deletions,comments
20699,7225,2023-11-02 06:35:22,open,0,1,0,,1,1,0,57.19,124654813.0,12.0,12.0,24.0,9.604,2,2,opened,0.0,1,0,1,1,0,0,1
20699,7224,2023-11-02 00:02:33,open,0,1,0,deps,1,1,0,57.19,124631244.0,7.0,7.0,14.0,9.604,1,1,opened,0.0,3,2,1,1,0,0,6
"""

df = pd.read_csv(StringIO(INLINE_CSV))
df['Creation_Date'] = pd.to_datetime(df['Creation_Date'], errors='coerce')
print('dtype before engine:', df['Creation_Date'].dtype)
print('values before engine:', df['Creation_Date'].tolist())

engine = MetricsEngine()
analysis = MagicMock()
analysis.config = {}
analysis.chart_type = 'bar'

config = analysis.config
print('config type:', type(config))

result_df = engine._apply_config(df, config)
print('After _apply_config dtype:', result_df['Creation_Date'].dtype)
print('After _apply_config values:', result_df['Creation_Date'].tolist())

df_copy = result_df.copy()
df_copy['Creation_Date'] = pd.to_datetime(df_copy['Creation_Date'], errors='coerce')
print('After re-parse values:', df_copy['Creation_Date'].tolist())
df_copy = df_copy.dropna(subset=['Creation_Date'])
print('After dropna rows:', len(df_copy))
