// function.h - 學生需要實作的函數宣告
// 此檔案將被學生提交的程式碼替換

// 1. 計算加權 GPA
double calculate_weighted_gpa(int scores[], int credits[], int n);

// 2. 計算班級排名（百分等級 PR 值）
int calculate_percentile_rank(int all_scores[], int n, int my_score);

// 3. 分數轉等第 GPA 點數
double score_to_gpa_points(int score);

// 4. 判斷是否達到畢業門檻
int check_graduation(double gpa, int total_credits, int required_credits,
                     int failed_subjects, int max_failed);
