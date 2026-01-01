#include <stdio.h>

int main(void) {
    FILE *fp = fopen("evaluation.json", "w");
    if (fp) {
        fprintf(fp, "{\n");
        fprintf(fp, "  \"evaluations\": [\n");
        fprintf(fp, "    {\"ta_name\": \"ChatGPT\", \"score\": 8, \"comment\": \"Clear and helpful explanations.\", \"strengths\": [\"Fast\", \"Friendly\"], \"improvements\": [\"Be more concise\"]},\n");
        fprintf(fp, "    {\"ta_name\": \"Gemini\", \"score\": 7, \"comment\": \"Useful but sometimes inconsistent.\", \"strengths\": [\"Creative\"], \"improvements\": [\"Stay consistent\"]},\n");
        fprintf(fp, "    {\"ta_name\": \"Opus\", \"score\": 9, \"comment\": \"Deep and structured guidance.\", \"strengths\": [\"Thorough\"], \"improvements\": [\"Shorten responses\"]}\n");
        fprintf(fp, "  ],\n");
        fprintf(fp, "  \"overall_comment\": \"Great support overall.\",\n");
        fprintf(fp, "  \"would_recommend\": true\n");
        fprintf(fp, "}\n");
        fclose(fp);
    }
    printf("Evaluation submitted successfully!\n");
    return 0;
}
