import streamlit as st
import sqlite3
import pandas as pd
import os
from typing import List, Dict, Any

class StreamlitDBManager:
    def __init__(self, db_path: str = "child_edu_ai.db"):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.connection = sqlite3.connect(self.db_path, timeout=30.0)
            return True
        except Exception as e:
            st.error(f"데이터베이스 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.connection:
            self.connection.close()
    
    def get_tables(self) -> List[str]:
        """테이블 목록 조회"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        return tables
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """테이블 스키마 조회"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'cid': row[0],
                'name': row[1],
                'type': row[2],
                'notnull': row[3],
                'default_value': row[4],
                'pk': row[5]
            })
        return columns
    
    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """SQL 쿼리 실행"""
        if not self.connection:
            self.connect()
        
        try:
            if params:
                df = pd.read_sql_query(query, self.connection, params=params)
            else:
                df = pd.read_sql_query(query, self.connection)
            return df
        except Exception as e:
            st.error(f"쿼리 실행 실패: {e}")
            return pd.DataFrame()
    
    def get_table_data(self, table_name: str, limit: int = 100) -> pd.DataFrame:
        """테이블 데이터 조회"""
        if not self.connection:
            self.connect()
        
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            df = pd.read_sql_query(query, self.connection)
            return df
        except Exception as e:
            st.error(f"테이블 데이터 조회 실패: {e}")
            return pd.DataFrame()

def main():
    st.set_page_config(
        page_title="SQLite 데이터베이스 관리자",
        page_icon="🗄️",
        layout="wide"
    )
    
    st.title("🗄️ SQLite 데이터베이스 관리자")
    st.markdown("---")
    
    # 데이터베이스 매니저 초기화
    db_manager = StreamlitDBManager()
    
    # 사이드바 - 데이터베이스 정보
    with st.sidebar:
        st.header("📊 데이터베이스 정보")
        
        if os.path.exists(db_manager.db_path):
            file_size = os.path.getsize(db_manager.db_path)
            st.metric("파일 크기", f"{file_size:,} bytes")
            
            if db_manager.connect():
                st.success("✅ 연결됨")
                tables = db_manager.get_tables()
                st.metric("테이블 수", len(tables))
            else:
                st.error("❌ 연결 실패")
        else:
            st.error(f"❌ 파일 없음: {db_manager.db_path}")
    
    # 메인 컨텐츠
    if not os.path.exists(db_manager.db_path):
        st.error(f"데이터베이스 파일 '{db_manager.db_path}'이 존재하지 않습니다.")
        return
    
    if not db_manager.connect():
        st.error("데이터베이스에 연결할 수 없습니다.")
        return
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📋 테이블 목록", "🔍 데이터 조회", "⚡ SQL 쿼리"])
    
    with tab1:
        st.header("📋 데이터베이스 테이블 목록")
        
        tables = db_manager.get_tables()
        if tables:
            for i, table_name in enumerate(tables, 1):
                with st.expander(f"{i}. {table_name}"):
                    # 테이블 스키마 표시
                    schema = db_manager.get_table_schema(table_name)
                    st.subheader("📐 스키마")
                    
                    schema_df = pd.DataFrame(schema)
                    st.dataframe(schema_df[['name', 'type', 'notnull', 'pk']], use_container_width=True)
                    
                    # 테이블 통계
                    try:
                        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                        count_df = db_manager.execute_query(count_query)
                        row_count = count_df.iloc[0]['count'] if not count_df.empty else 0
                        st.metric("총 행 수", row_count)
                        
                        if row_count > 0:
                            # 샘플 데이터 표시
                            st.subheader("📄 샘플 데이터 (처음 10행)")
                            sample_df = db_manager.get_table_data(table_name, limit=10)
                            st.dataframe(sample_df, use_container_width=True)
                    except Exception as e:
                        st.error(f"테이블 정보 조회 실패: {e}")
        else:
            st.info("데이터베이스에 테이블이 없습니다.")
    
    with tab2:
        st.header("🔍 데이터 조회")
        
        tables = db_manager.get_tables()
        if tables:
            selected_table = st.selectbox("테이블 선택:", tables)
            
            if selected_table:
                col1, col2 = st.columns(2)
                
                with col1:
                    limit = st.number_input("조회할 행 수:", min_value=1, max_value=1000, value=100)
                
                with col2:
                    if st.button("데이터 조회", type="primary"):
                        with st.spinner("데이터를 조회하는 중..."):
                            df = db_manager.get_table_data(selected_table, limit=limit)
                            if not df.empty:
                                st.success(f"✅ {len(df)}행을 조회했습니다.")
                                st.dataframe(df, use_container_width=True)
                                
                                # 데이터 다운로드 버튼
                                csv = df.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="📥 CSV 다운로드",
                                    data=csv,
                                    file_name=f"{selected_table}_data.csv",
                                    mime="text/csv"
                                )
                            else:
                                st.warning("조회된 데이터가 없습니다.")
        else:
            st.info("조회할 테이블이 없습니다.")
    
    with tab3:
        st.header("⚡ SQL 쿼리 실행")
        
        # 쿼리 입력
        query = st.text_area(
            "SQL 쿼리를 입력하세요:",
            height=150,
            placeholder="SELECT * FROM table_name LIMIT 10;"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("실행", type="primary"):
                if query.strip():
                    with st.spinner("쿼리를 실행하는 중..."):
                        try:
                            df = db_manager.execute_query(query)
                            if not df.empty:
                                st.success(f"✅ 쿼리가 성공적으로 실행되었습니다. ({len(df)}행)")
                                st.dataframe(df, use_container_width=True)
                                
                                # 결과 다운로드
                                csv = df.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="📥 결과 다운로드",
                                    data=csv,
                                    file_name="query_result.csv",
                                    mime="text/csv"
                                )
                            else:
                                st.info("쿼리가 실행되었지만 결과가 없습니다.")
                        except Exception as e:
                            st.error(f"쿼리 실행 실패: {e}")
                else:
                    st.warning("쿼리를 입력해주세요.")
        
        with col2:
            st.markdown("""
            **💡 예시 쿼리:**
            - `SELECT * FROM table_name LIMIT 10;`
            - `SELECT COUNT(*) FROM table_name;`
            - `PRAGMA table_info(table_name);`
            """)
    
    # 연결 해제
    db_manager.disconnect()

if __name__ == "__main__":
    main() 