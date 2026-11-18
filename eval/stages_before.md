| 案例 | 模式 | 條 | 預期 | 擷取 | 檢索 | 規則 | AI | 最終 | 最終條號 |
|---|---|---|---|---|---|---|---|---|---|
| a_marketing | rule | 2 | 20 | ✓ | ✗ | ✓ | - | ✓ | 20 |
| a_marketing | rule | 4 | 11 | ✓ | ✓ | ✓ | - | ✓ | 11 |
| a_marketing | rule | 6 | 12 | ✓ | ✓ | ✓ | - | ✓ | 12 |
| a_marketing | rule+ai | 2 | 20 | ✓ | ✗ | ✓ | ✗ | ✓ | 20,20-1 |
| a_marketing | rule+ai | 4 | 11 | ✓ | ✓ | ✓ | ✗ | ✓ | 11 |
| a_marketing | rule+ai | 6 | 12 | ✓ | ✓ | ✓ | ✓ | ✓ | 12 |
| b_hr | rule | 2 | 6 | ✓ | ✗ | ✓ | - | ✓ | 6 |
| b_hr | rule | 4 | 20 | ✓ | ✗ | ✓ | - | ✓ | 20 |
| b_hr | rule | 6 | 11 | ✓ | ✓ | ✓ | - | ✓ | 11 |
| b_hr | rule+ai | 2 | 6 | ✓ | ✗ | ✓ | ✗ | ✓ | 6,11 |
| b_hr | rule+ai | 4 | 20 | ✓ | ✗ | ✓ | ✗ | ✓ | 20 |
| b_hr | rule+ai | 6 | 11 | ✓ | ✓ | ✓ | ✗ | ✓ | 11 |
| c_cloud | rule | 2 | 21 | ✓ | ✗ | ✓ | - | ✓ | 21 |
| c_cloud | rule | 3 | 12 | ✓ | ✓ | ✓ | - | ✓ | 12 |
| c_cloud | rule | 5 | 20 | ✓ | ✗ | ✓ | - | ✓ | 20 |
| c_cloud | rule+ai | 2 | 21 | ✓ | ✗ | ✓ | ✗ | ✓ | 21,12 |
| c_cloud | rule+ai | 3 | 12 | ✓ | ✓ | ✓ | ✓ | ✓ | 12 |
| c_cloud | rule+ai | 5 | 20 | ✓ | ✗ | ✓ | ✗ | ✓ | 20,10 |
| d_holdout | rule | 2 | 20 | ✓ | ✗ | ✗ | - | ✗ | — |
| d_holdout | rule | 4 | 11 | ✓ | ✓ | ✗ | - | ✗ | — |
| d_holdout | rule | 5 | 21 | ✓ | ✗ | ✗ | - | ✗ | — |
| d_holdout | rule+ai | 2 | 20 | ✓ | ✗ | ✗ | ✗ | ✗ | — |
| d_holdout | rule+ai | 4 | 11 | ✓ | ✓ | ✗ | ✗ | ✗ | — |
| d_holdout | rule+ai | 5 | 21 | ✓ | ✗ | ✗ | ✗ | ✗ | 20-1 |

| 案例 | 模式 | 條款數(實際/預期) | 命中 | 誤報(乾淨條款) | AI 失敗次數 | 秒 |
|---|---|---|---|---|---|---|
| a_marketing | rule | 7/7 | 3/3 | 0  | 0 | 0.1 |
| a_marketing | rule+ai | 7/7 | 3/3 | 2 3→42(ai); 5→11(ai) | 0 | 74.4 |
| b_hr | rule | 8/8 | 3/3 | 0  | 0 | 0.0 |
| b_hr | rule+ai | 8/8 | 3/3 | 1 7→12(ai) | 0 | 234.6 |
| c_cloud | rule | 7/7 | 3/3 | 0  | 0 | 0.0 |
| c_cloud | rule+ai | 7/7 | 3/3 | 2 6→41(ai); 7→20-1(ai) | 0 | 133.1 |
| d_holdout | rule | 7/7 | 0/3 | 0  | 0 | 0.0 |
| d_holdout | rule+ai | 7/7 | 0/3 | 0  | 0 | 105.5 |
