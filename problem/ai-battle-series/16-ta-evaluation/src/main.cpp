#include <bits/stdc++.h>
using namespace std;

int main() {
    ofstream fout("evaluation.json");
    if (fout) {
        fout << "{\n";
        fout << "  \"evaluations\": [\n";
        fout << "    {\"ta_name\": \"ChatGPT\", \"score\": 8, \"comment\": \"Clear and helpful explanations.\", \"strengths\": [\"Fast\", \"Friendly\"], \"improvements\": [\"Be more concise\"]},\n";
        fout << "    {\"ta_name\": \"Gemini\", \"score\": 7, \"comment\": \"Useful but sometimes inconsistent.\", \"strengths\": [\"Creative\"], \"improvements\": [\"Stay consistent\"]},\n";
        fout << "    {\"ta_name\": \"Opus\", \"score\": 9, \"comment\": \"Deep and structured guidance.\", \"strengths\": [\"Thorough\"], \"improvements\": [\"Shorten responses\"]}\n";
        fout << "  ],\n";
        fout << "  \"overall_comment\": \"Great support overall.\",\n";
        fout << "  \"would_recommend\": true\n";
        fout << "}\n";
    }
    cout << "Evaluation submitted successfully!\n";
    return 0;
}
