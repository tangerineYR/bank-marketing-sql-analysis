import streamlit as st
from scoring import JOBS, MONTHS, CONTACTS, OUTCOMES, score_marketing_priority

st.title('정기예금 마케팅 우선순위')
st.caption('과거 SQL 분석을 참고해 사람이 정한 규칙 점수입니다. 통계적으로 학습된 확률 모델이 아닙니다.')
col1, col2 = st.columns(2)
with col1:
    age = st.number_input('나이', min_value=18, max_value=100, value=35)
    job = st.selectbox('직업', JOBS)
with col2:
    month = st.selectbox('연락 월', MONTHS)
    contact = st.selectbox('연락 방식', CONTACTS)
previous_outcome = st.radio('이전 캠페인 결과', OUTCOMES)
if st.button('우선순위 확인'):
    result = score_marketing_priority(age, job, month, contact, previous_outcome)
    st.subheader(result.grade)
    st.metric('규칙 점수', result.score)
    st.caption('점수 범위: -1~13 · 8점 이상 최우선 / 5~7점 우선 / 3~4점 일반 검토 / 3점 미만 낮은 우선순위')
    for reason in result.reasons:
        st.write(reason)
    st.caption('과거 집단별 가입률은 마케팅의 인과 효과를 의미하지 않습니다.')
