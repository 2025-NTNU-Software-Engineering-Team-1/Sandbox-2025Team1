#include <stdio.h>

int main(void) {
    FILE *fp = fopen("evaluation.json", "w");
    if (fp) {
        fprintf(fp, "{
");
        fprintf(fp, "  "evaluations": [
");
        fprintf(fp, "    {"ta_name": "ChatGPT", "score": 8, "comment": "Clear and helpful explanations.", "strengths": ["Fast", "Friendly"], "improvements": ["Be more concise"]},
");
        fprintf(fp, "    {"ta_name": "Gemini", "score": 7, "comment": "Useful but sometimes inconsistent.", "strengths": ["Creative"], "improvements": ["Stay consistent"]},
");
        fprintf(fp, "    {"ta_name": "Opus", "score": 9, "comment": "Deep and structured guidance.", "strengths": ["Thorough"], "improvements": ["Shorten responses"]}
");
        fprintf(fp, "  ],
");
        fprintf(fp, "  "overall_comment": "Great support overall.",
");
        fprintf(fp, "  "would_recommend": true
");
        fprintf(fp, "}
");
        fclose(fp);
    }
    printf("Evaluation submitted successfully!
");
    return 0;
}
