#include <iostream>
#include <string>
#include <curl/curl.h>

// 用於儲存HTTP回應的回調函數
size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* data) {
    size_t totalSize = size * nmemb;
    data->append((char*)contents, totalSize);
    return totalSize;
}

int main() {
    int n;
    std::cin >> n;
    
    // 初始化 libcurl
    curl_global_init(CURL_GLOBAL_DEFAULT);
    
    for (int i = 0; i < n; i++) {
        std::string param;
        std::cin >> param;
        
        // 構建完整的URL
        std::string url = "http://localhost:8080/api/data/" + param;
        
        // 創建 curl handle
        CURL* curl = curl_easy_init();
        if (curl) {
            std::string response;
            
            // 設置URL
            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            
            // 設置回調函數來接收回應
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
            
            // 執行請求
            CURLcode res = curl_easy_perform(curl);
            
            if (res == CURLE_OK) {
                // 輸出回應內容
                std::cout << response << std::endl;
            } else {
                std::cerr << "curl_easy_perform() failed: " << curl_easy_strerror(res) << std::endl;
            }
            
            curl_easy_cleanup(curl);
        }
    }
    
    curl_global_cleanup();
    return 0;
}
