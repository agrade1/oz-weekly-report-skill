:::writing{variant="document" id="{{fresh_five_digit_id}}"}
## 정량 보고

**지난주**

| **운영 만족도** | {{previous_operation_with_response_count}} |
| --- | --- |
| **콘텐츠 만족도** | {{previous_content}} |
| **실시간 만족도** | {{previous_live}} |
| **과제 만족도** | {{previous_assignment}} |
| **교과목 만족도** | {{previous_achievement}} |

**이번주**

| **운영 만족도** | {{current_operation_with_response_count}} |  |
| --- | --- | --- |
| **콘텐츠 만족도** | {{current_content}} | {{learning_subject}} |
| **실시간 만족도** | {{current_live}} |  |
| **과제 만족도** | {{current_assignment}} |  |
| **교과목 만족도** | {{current_achievement}} |  |

## 미응답 수강생

- **운영 만족도 ({{operation_missing_count}}명)**: {{operation_missing_names_or_none}}
- **학습 만족도 - {{learning_subject}} ({{learning_missing_count}}명)**: {{learning_missing_names_or_none}}

- **데이터 확인 필요**
  - {{dashboard_and_roster_count_warning}}

## 특이사항

- **{{name}} — {{problem_summary}}**
  
  `상황`
  
  - {{situation_fact_sentence}}
  
  `운영진 대응 및 결과`
  
  - {{source_backed_operator_response_or_no_confirmed_response}}

## 📊 {{operation_date_mm_dd}} 운만조 VOC 요약

- **긍정 피드백**
  - {{operation_positive_short_original}}
  - {{operation_positive_long_summary}} ({{operation_positive_long_name}}님)
    - 원문 보기
      - {{operation_positive_long_original}}
- **개선 및 제안 사항**
  - {{operation_improvement_short_original}} ({{respondent_name}}님 - {{operation_improvement_score}}점)
  - {{operation_improvement_long_summary}} ({{operation_improvement_long_name}}님 - {{operation_improvement_score}}점)
    - 원문 보기
      - {{operation_improvement_long_original}}

## 📊 {{learning_date_mm_dd}} 학만조 VOC _{{learning_subject}}

- **긍정 피드백**
  - {{learning_positive_short_original}}
  - {{learning_positive_long_summary}} ({{learning_positive_long_name}}님)
    - 원문 보기
      - {{learning_positive_long_original}}
- **개선 및 제안 사항**
  - {{learning_improvement_short_original}} ({{respondent_name}}님 - {{learning_improvement_score_label}})
  - {{learning_improvement_long_summary}} ({{learning_improvement_long_name}}님 - {{learning_improvement_score_label}})
    - 원문 보기
      - {{learning_improvement_long_original}}

## 운영 대시보드 입력용

| 대시보드 구분 | 만족도 | 응답 인원 | 현재 인원 | 실시일 |
| --- | --- | --- | --- | --- |
| 라이브 세션 만족도 | {{current_live}} | {{learning_respondents}}명 | {{current_students}}명 | {{learning_date_iso}} |
| 과제 만족도 | {{current_assignment}} | {{learning_respondents}}명 | {{current_students}}명 | {{learning_date_iso}} |
| 성취도 | {{current_achievement}} | {{learning_respondents}}명 | {{current_students}}명 | {{learning_date_iso}} |
| VOD 만족도 | {{current_content}} | {{learning_respondents}}명 | {{current_students}}명 | {{learning_date_iso}} |
:::
