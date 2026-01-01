#include <stdio.h>
#include <string.h>

static double compute_gpa(const char *filename) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        return 0.0;
    }
    char line[256];
    if (!fgets(line, sizeof(line), fp)) {
        fclose(fp);
        return 0.0;
    }
    double total_points = 0.0;
    double total_credits = 0.0;
    while (fgets(line, sizeof(line), fp)) {
        char *course = strtok(line, ",");
        char *name = strtok(NULL, ",");
        char *credits_str = strtok(NULL, ",");
        char *grade_str = strtok(NULL, ",\r\n");
        if (!course || !name || !credits_str || !grade_str) {
            continue;
        }
        int credits = atoi(credits_str);
        int grade = atoi(grade_str);
        total_points += credits * grade;
        total_credits += credits;
    }
    fclose(fp);
    if (total_credits <= 0.0) {
        return 0.0;
    }
    return total_points / total_credits;
}

static void write_certificate(const char *student_id, const char *name,
                              const char *department, int year, double gpa) {
    FILE *fp = fopen("certificate.txt", "w");
    if (!fp) {
        return;
    }
    fprintf(fp, "GRADUATION CERTIFICATE\n");
    fprintf(fp, "Student ID: %s\n", student_id);
    fprintf(fp, "Name: %s\n", name);
    fprintf(fp, "Department: %s\n", department);
    fprintf(fp, "GPA: %.2f\n", gpa);
    fprintf(fp, "Graduation Year: %d\n", year);
    fclose(fp);
}

int main(void) {
    int n = 0;
    if (scanf("%d", &n) != 1) {
        return 0;
    }
    int low = 1000;
    int high = n;
    char response[16];

    while (low <= high) {
        int mid = low + (high - low) / 2;
        printf("guess %d\n", mid);
        fflush(stdout);
        if (scanf("%15s", response) != 1) {
            return 0;
        }
        if (strcmp(response, "CORRECT") == 0) {
            break;
        }
        if (strcmp(response, "HIGHER") == 0) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    double gpa = compute_gpa("transcript.csv");
    write_certificate("B12345678", "王小明", "資訊工程學系", 2024, gpa);
    printf("GPA: %.6f\n", gpa);
    return 0;
}
