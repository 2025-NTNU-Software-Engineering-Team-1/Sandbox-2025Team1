#include <bits/stdc++.h>
using namespace std;

int main() {
    ofstream fout("evaluation.json");
    if (fout) {
        fout << "{
";
        fout << "  "evaluations": [
";
        fout << "    {"ta_name": "ChatGPT", "score": 8, "comment": "Clear and helpful explanations.", "strengths": ["Fast", "Friendly"], "improvements": ["Be more concise"]},
";
        fout << "    {"ta_name": "Gemini", "score": 7, "comment": "Useful but sometimes inconsistent.", "strengths": ["Creative"], "improvements": ["Stay consistent"]},
";
        fout << "    {"ta_name": "Opus", "score": 9, "comment": "Deep and structured guidance.", "strengths": ["Thorough"], "improvements": ["Shorten responses"]}
";
        fout << "  ],
";
        fout << "  "overall_comment": "Great support overall.",
";
        fout << "  "would_recommend": true
";
        fout << "}
";
    }
    cout << "Evaluation submitted successfully!
";
    return 0;
}
