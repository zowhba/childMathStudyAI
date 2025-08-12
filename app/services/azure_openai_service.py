from openai import AzureOpenAI
from jinja2 import Environment, FileSystemLoader
import os
import uuid
from dotenv import load_dotenv
# from langfuse import Langfuse, Trace  # langfuse 관련 import 제거

# langfuse = Langfuse(
#     public_key="pk-lf-0aac3129-100a-4e8f-bac7-7d66539e16ae",
#     secret_key="sk-lf-f12705b9-29ae-4533-a55d-e7831edb36ae",
#     host="https://us.cloud.langfuse.com"  # 또는 클라우드 주소
# )

# Jinja2 템플릿 로더 설정
template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts')
env = Environment(loader=FileSystemLoader(template_dir))



class AzureOpenAIService:
    def __init__(self, endpoint, key, dep_curriculum, dep_embed):
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        load_dotenv(dotenv_path)
        
        # Azure OpenAI 클라이언트 직접 초기화 (환경변수 의존성 제거)
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version="2024-05-01-preview"
        )
        
        self.dep_curriculum = dep_curriculum
        self.dep_embed = dep_embed

    def get_initial_curriculum(self, profile):
        """아동 프로필 기반 초기 학습 주제 생성"""
        tmpl = env.get_template("initial_curriculum.txt")
        prompt = tmpl.render(
            name=profile.name,
            grade=profile.grade,
            semester=profile.semester
        )
        resp = self.client.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "초등 수학 교육과정 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()

    def get_embedding(self, text: str) -> list:
        """텍스트를 임베딩 벡터로 변환"""
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.dep_embed
            )
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            print(f"임베딩 생성 실패 - Model: {self.dep_embed}")
            print(f"Error: {e}")
            raise e

    def generate_materials(self, curriculum_text: str, docs: list):
        """커리큘럼 및 유사 자료를 바탕으로 교재 및 평가 문제 생성"""
        tmpl = env.get_template("materials.txt")
        # 구버전 호환용: curriculum/doc 기반 렌더링은 더 이상 사용하지 않음
        prompt = tmpl.render(grade=0, semester=0, topic="")
        resp = self.client.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "교재 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        content = resp.choices[0].message.content.strip()
        
        # 문제와 정답, 해설을 분리
        lesson = content
        materials = [content]
        return lesson, materials

    def _select_topic(self, grade: int, semester: int) -> str:
        """리소스에서 학년/학기에 맞는 주제를 선택"""
        import json
        resource_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resource', 'curriculum.json')
        try:
            with open(resource_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                if item.get('grade') == grade and item.get('semester') == semester:
                    subjects = item.get('subjects') or []
                    return subjects[0] if subjects else "기본 연산"
        except Exception:
            pass
        return "기본 연산"

    def _get_curriculum_data(self):
        import json
        resource_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resource', 'curriculum.json')
        with open(resource_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_allowed_topics(self, grade: int, semester: int):
        data = self._get_curriculum_data()
        allowed = []
        for item in data:
            g = int(item.get('grade', 0))
            s = int(item.get('semester', 0))
            if g < grade or (g == grade and s <= semester):
                allowed.extend(item.get('subjects') or [])
        # 중복 제거, 길이 순 정렬(긴 용어 우선 매칭 대비)
        return sorted(set(allowed), key=lambda x: (-len(x), x))

    def _get_banned_topics(self, grade: int, semester: int):
        data = self._get_curriculum_data()
        banned = []
        for item in data:
            g = int(item.get('grade', 0))
            s = int(item.get('semester', 0))
            if g > grade or (g == grade and s > semester):
                banned.extend(item.get('subjects') or [])
        return sorted(set(banned), key=lambda x: (-len(x), x))

    def _expand_terms(self, terms: list[str]) -> list[str]:
        # 금지 과목명을 소단어로 분해해 포착률 향상(예: "분수와 소수" -> ["분수", "소수"]) 
        import re
        tokens: set[str] = set()
        for t in terms:
            if not t:
                continue
            # 1) 기본 전체 문자열도 포함
            tokens.add(t.strip())
            # 2) 구분자 기준 분해
            parts = re.split(r"[\s/·\-\+\(\),]", t)
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                # 3) '와/과/및/의' 결합 분해
                for sub in re.split(r"[와과및의]", p):
                    sub = sub.strip()
                    if len(sub) >= 2:
                        tokens.add(sub)
        return sorted(tokens, key=lambda x: (-len(x), x))

    def _contains_banned_terms(self, text: str, banned_terms: list[str]) -> bool:
        lowered = text.lower()
        for t in banned_terms:
            if not t:
                continue
            if t.lower() in lowered:
                return True
        return False

    def generate_materials_for_grade_semester(self, grade: int, semester: int, docs: list):
        """학년/학기/주제 기반 문제 생성"""
        tmpl = env.get_template("materials.txt")
        topic = self._select_topic(grade, semester)
        allowed = self._get_allowed_topics(grade, semester)
        banned = self._get_banned_topics(grade, semester)

        def _build_prompt():
            base = tmpl.render(grade=grade, semester=semester, topic=topic)
            guide = (
                "\n\n[허용 주제]\n- " + "\n- ".join(allowed[:12]) +
                "\n\n[금지 주제]\n- " + ("\n- ".join(banned[:12]) if banned else "(없음)") +
                "\n\n주의: 문항은 허용 주제 범위에서만 출제하고, 금지 주제가 언급되면 무효입니다."
            )
            return base + guide

        sys_msg = (
            "너는 한국 초등 수학 출제 교사다. 반드시 모호성 없이, 정답이 하나만 되도록 출제한다. "
            "현재 학기까지 배운 개념만 사용하고, 응용은 과거 학기 개념과만 혼합한다. 상위 학년 개념 금지."
        )

        max_retry = 2
        content = ""
        banned_terms_expanded = self._expand_terms(banned)
        for attempt in range(max_retry + 1):
            prompt = _build_prompt() if attempt == 0 else (_build_prompt() + "\n\n이전 시도에서 금지 주제가 포함되었습니다. 금지 주제를 절대 사용하지 말고 다시 출제하세요.")
            resp = self.client.chat.completions.create(
                model=self.dep_curriculum,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user",   "content": prompt}
                ]
            )
            content = resp.choices[0].message.content.strip()
            if not self._contains_banned_terms(content, banned_terms_expanded):
                break

        # Worksheet/AnswerKey 분리
        worksheet, answer_key = content, ""
        if "[AnswerKey]" in content:
            parts = content.split("[AnswerKey]")
            worksheet = parts[0].strip()
            answer_key = parts[1].strip() if len(parts) > 1 else ""
        lesson = f"[{grade}학년 {semester}학기] {topic}\n\n" + worksheet
        materials = [worksheet + ("\n\n[AnswerKey]\n" + answer_key if answer_key else "")]
        return lesson, materials

    def save_lesson(self, child_id, lesson_text, docs):
        """학습 세션 ID 생성 및 저장"""
        lesson_id = str(uuid.uuid4())
        # TODO: 필요 시 저장 로직 추가
        return lesson_id

    def create_feedback(self, materials_text, responses_text):
        tmpl = env.get_template("feedback.txt")
        prompt = tmpl.render(materials=materials_text, responses=responses_text)
        
        # Langfuse trace 시작 (임시 주석 처리)
        # trace = Trace(
        #     name="create_feedback",
        #     user_id="some_user_id",  # 필요시 아동 ID 등
        #     langfuse=langfuse
        # )
        # span = trace.span(
        #     name="openai-feedback-call",
        #     input=prompt
        # )
        resp = self.client.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "피드백 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        output = resp.choices[0].message.content.strip()
        print("[Langfuse Output]", repr(output))  # 값이 정확히 뭔지 확인
        # span.output = str(output)  # 혹시 모르니 str로 변환
        # span.end()
        return output

    # ===== Deterministic MCQ grading for consistency =====
    def _parse_worksheet_and_key(self, materials_text: str):
        import re
        worksheet = materials_text
        answer_key = ""
        if "[Worksheet]" in materials_text:
            parts = materials_text.split("[Worksheet]")
            worksheet = parts[-1]
        if "[AnswerKey]" in worksheet:
            wk, ak = worksheet.split("[AnswerKey]", 1)
            worksheet = wk.strip()
            answer_key = ak.strip()

        # Parse problems
        problems = []
        pattern = re.compile(r"\[Problem\s*(\d+)\]\s*", re.IGNORECASE)
        matches = list(pattern.finditer(worksheet))
        for idx, m in enumerate(matches):
            start = m.end()
            end = matches[idx+1].start() if idx+1 < len(matches) else len(worksheet)
            block = worksheet[start:end].strip()
            number = int(m.group(1)) if m.group(1).isdigit() else (idx+1)
            # split stem and choices
            stem = block
            choices_block = ""
            if "Choices:" in block:
                parts2 = block.split("Choices:", 1)
                stem = parts2[0].strip()
                choices_block = parts2[1]
            def pick(label):
                mm = re.search(rf"\b{label}\)\s*(.+)", choices_block)
                return mm.group(1).strip() if mm else ""
            problems.append({
                "number": number,
                "stem": stem,
                "choices": {
                    "A": pick("A"),
                    "B": pick("B"),
                    "C": pick("C"),
                    "D": pick("D"),
                }
            })

        # Parse answer key lines like: 1) A
        key_map = {}
        for line in answer_key.splitlines():
            line = line.strip()
            mm = re.match(r"(\d+)\)\s*([ABCD])", line, re.IGNORECASE)
            if mm:
                key_map[int(mm.group(1))] = mm.group(2).upper()

        return problems, key_map

    def _parse_student_responses(self, responses_text: str):
        import re
        resp_map = {}
        for line in responses_text.splitlines():
            mm = re.search(r"(\d+)\s*번\s*답\s*:\s*([ABCD])", line, re.IGNORECASE)
            if mm:
                resp_map[int(mm.group(1))] = mm.group(2).upper()
        return resp_map

    def grade_multiple_choice(self, materials_text: str, responses_text: str) -> str:
        """결정론적 채점 + LLM 해설(정답 표기는 코드에서 강제)로 안전하게 결과 생성"""
        problems, key_map = self._parse_worksheet_and_key(materials_text)
        resp_map = self._parse_student_responses(responses_text)
        total = len(problems) if problems else 0
        correct = 0
        per_q = []
        for p in problems:
            n = p["number"]
            correct_opt = key_map.get(n, "")
            student_opt = resp_map.get(n, "")
            is_correct = (bool(correct_opt) and bool(student_opt) and correct_opt == student_opt)
            if is_correct:
                correct += 1
            per_q.append({
                "number": n,
                "stem": p["stem"],
                "choices": p["choices"],
                "correct": correct_opt,
                "student": student_opt,
                "ok": is_correct
            })
        score = int(round((correct / total) * 100)) if total > 0 else 0

        # 1) [Score]
        score_md = f"[Score]\n총점: {score} 점\n\n"

        # 2) [PerQuestion] - 결정론적 생성, O/X 표기
        perq_lines = ["[PerQuestion]"]
        for x in per_q:
            n = x["number"]
            st_sel = x["student"] or "-"
            corr = x["correct"] or "-"
            px = "O" if x["ok"] else "X"
            perq_lines.append(f"{n}) 학생: ({st_sel}) | 정답: ({corr}) | 채점: {px}")
        perq_md = "\n".join(perq_lines) + "\n\n"

        # 3) [Explanations] - LLM에 '해설만' 요청 후, 정답 표기는 코드에서 강제 삽입
        import json as _json
        expl_system = (
            "한국 초등 수학 해설 작성기. 주어진 문항(stem)과 선택지(choices)를 참고해, 각 문항의 해설 본문만 1~3문장으로 작성. "
            "정답 글자(A/B/C/D)나 학생 선택, 점수, Correct/O/X는 출력하지 말 것. 새 문제를 만들지 말 것."
        )
        expl_payload = {
            "items": [
                {
                    "number": x["number"],
                    "stem": x["stem"],
                    "choices": x["choices"],
                    "correct": x["correct"],
                    "student": x["student"],
                    "ok": x["ok"],
                } for x in per_q
            ]
        }
        try:
            expl_resp = self.client.chat.completions.create(
                model=self.dep_curriculum,
                messages=[
                    {"role": "system", "content": expl_system},
                    {"role": "user", "content": (
                        "다음 JSON을 참고하여 각 번호별로 한 줄씩 'n) 해설: ...' 형식으로 출력하세요. "
                        "틀린 문항은 더 자세하고 친절하게, 쉬운 예 1개를 포함하세요.\n\nJSON:\n" + _json.dumps(expl_payload, ensure_ascii=False)
                    )}
                ]
            )
            expl_text = expl_resp.choices[0].message.content.strip()
        except Exception:
            expl_text = ""

        # 파싱하여 번호→해설 매핑
        exp_map = {}
        for line in expl_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # 형태: 'n) 해설: ...'
            import re as _re
            m = _re.match(r"(\d+)\)\s*해설\s*:\s*(.+)", line)
            if m:
                exp_map[int(m.group(1))] = m.group(2).strip()

        # 결정론적 [Explanations]
        expl_lines = ["[Explanations]"]
        for x in per_q:
            n = x["number"]
            corr = x["correct"] or "-"
            body = exp_map.get(n, "간단한 풀이 과정을 따라 정답 보기를 확인해 보세요.")
            # 틀린 문항은 해설을 조금 더 강조
            if not x["ok"] and body:
                body = body + " 추가로, 비슷한 쉬운 예를 만들어 연습해 보세요."
            expl_lines.append(f"{n}) 정답: ({corr}) - {body}")
        expl_md = "\n".join(expl_lines) + "\n\n"

        # 4) [Feedback] - 간단 규칙 기반 생성
        wrong_nums = [str(x["number"]) for x in per_q if not x["ok"]]
        if score >= 90:
            fb_text = "아주 훌륭해요! 개념 이해가 잘 되어 있어요. 다음에는 응용 문제에 더 도전해 봅시다."
        elif score >= 70:
            fb_text = (
                "좋아요! 조금만 더 연습하면 더 높은 점수를 받을 수 있어요. "
                + (f"틀린 문항: {', '.join(wrong_nums)}. " if wrong_nums else "")
                + "틀린 유형의 개념을 복습해 봅시다."
            )
        else:
            fb_text = (
                "괜찮아요, 기초부터 차근차근 다시 연습해 볼까요? "
                + (f"틀린 문항: {', '.join(wrong_nums)}. " if wrong_nums else "")
                + "덧셈/뺄셈/도형 기초를 복습하고 쉬운 문제부터 풀어봐요."
            )
        feedback_md = "[Feedback]\n" + fb_text + "\n"

        return score_md + perq_md + expl_md + feedback_md

    def create_overall_feedback(self, name, grade, semester, history):
        """학생의 학습 이력과 피드백을 바탕으로 종합 피드백 생성"""
        tmpl = env.get_template("feedback_summary.txt")
        prompt = tmpl.render(name=name, grade=grade, semester=semester, history=history)

        # Langfuse trace 시작 (임시 주석 처리)
        # trace = Trace(
        #     name="create_overall_feedback",
        #     user_id=name,  # 필요시 child_id 등으로 변경
        #     langfuse=langfuse
        # )
        # span = trace.span(
        #     name="openai-overall-feedback-call",
        #     input=prompt
        # )
        resp = self.client.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "종합 피드백 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        output = resp.choices[0].message.content.strip()
        # span.output = output
        # span.end()
        return output

    def generate_next_material(self, child_id, lesson_id, last_responses=None):
        """이전 학습 반영하여 다음 교재 생성"""
        tmpl = env.get_template("next_material.txt")
        # next_material 템플릿은 이름/학년/학기/이전 주제/피드백을 기대
        prompt = tmpl.render(name=child_id, grade=0, semester=0, topic="", feedback=str(last_responses or ""))
        resp = self.client.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": "다음 교재 생성 AI"},
                {"role": "user",   "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    
    def generate_materials_for_grade_semester_with_rag(self, grade: int, semester: int, related_docs, curriculum_units=None, curriculum_guide="", specified_subject=None, extra_request=None):
        """RAG 시스템을 활용한 고품질 문제 생성"""
        from typing import List
        import random
        
        # 단원이 없으면 기존 방식으로 fallback
        if not curriculum_units:
            return self.generate_materials_for_grade_semester(grade, semester, related_docs)
        
        # 지정된 단원이 있으면 우선 사용, 없으면 랜덤 선택
        if specified_subject and specified_subject in curriculum_units:
            selected_unit = specified_subject
        else:
            selected_unit = random.choice(curriculum_units)
        
        # 교육과정 가이드 정보를 포함한 시스템 메시지 구성
        enhanced_system_message = f"""당신은 초등학교 수학 문제 출제 전문가입니다.

현재 대상: {grade}학년 {semester}학기
선택된 단원: {selected_unit}

교육과정 가이드 정보:
{curriculum_guide if curriculum_guide else "해당 단원에 대한 가이드 정보가 없습니다."}

다음 지침을 엄격히 따라주세요:
1. 선택된 단원에 정확히 맞는 문제만 출제
2. 교육과정 가이드의 수준과 범위를 준수
3. 문제 난이도를 단계별로 구성 (기본→추론→응용→고급응용)
4. 모든 문제는 4지선다 형태 (A, B, C, D)
5. 명확하고 모호하지 않은 문제 구성
6. (있다면) 사용자의 추가 요청을 최대 100자 범위 내에서 반영
"""
        
        # 기존 템플릿 활용하되 단원 정보 추가
        tmpl = env.get_template("materials.txt")
        curriculum_text = f"{grade}학년 {semester}학기 수학 - {selected_unit}"
        
        prompt = tmpl.render(
            curriculum=curriculum_text,
            docs=related_docs[:3] if related_docs else []
        )
        
        # 교육과정 가이드 정보가 있으면 프롬프트에 추가
        if curriculum_guide:
            prompt += f"\n\n[교육과정 가이드 참고]\n{curriculum_guide[:1000]}"  # 길이 제한
        if extra_request:
            prompt += f"\n\n[추가 요청]\n{str(extra_request)[:100]}"
        
        resp = self.client.chat.completions.create(
            model=self.dep_curriculum,
            messages=[
                {"role": "system", "content": enhanced_system_message},
                {"role": "user", "content": prompt}
            ]
        )
        
        lesson_content = resp.choices[0].message.content.strip()
        
        # 간단한 문자열 파싱 (RAG용)
        worksheet = lesson_content
        answer_key = ""
        
        if "[Worksheet]" in lesson_content:
            parts = lesson_content.split("[Worksheet]")
            worksheet = parts[-1]
        if "[AnswerKey]" in worksheet:
            wk, ak = worksheet.split("[AnswerKey]", 1)
            worksheet = wk.strip()
            answer_key = ak.strip()
        
        # 선택된 단원을 제목에 포함
        lesson = f"[{grade}학년 {semester}학기] {selected_unit}\n\n{lesson_content}"
        materials = [worksheet + ("\n\n[AnswerKey]\n" + answer_key if answer_key else "")]
        
        return lesson, materials 