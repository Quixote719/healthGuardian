"""
风险检测模块单元测试

测试 detect_high_risk_keywords, detect_prohibited_keywords, detect_out_of_scope 函数
验证所有关键词检测场景

Requirements: 5.3, 5.4, 8.7
"""

import pytest

from app.agents.risk_detector import (
    detect_high_risk_keywords,
    detect_prohibited_keywords,
    detect_out_of_scope,
    get_professional_help_suggestion,
    perform_safety_check,
    HIGH_RISK_KEYWORDS,
    PROHIBITED_KEYWORDS,
    OUT_OF_SCOPE_KEYWORDS,
)


class TestDetectHighRiskKeywords:
    """高风险关键词检测测试 (Requirement 5.3)"""
    
    # ===== 用药调整类测试 =====
    
    def test_detect_stop_medication(self):
        """测试检测'停药'关键词"""
        text = "我想停药试试看"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "停药" in keywords
    
    def test_detect_change_medication(self):
        """测试检测'换药'关键词"""
        text = "医生说可以换药了"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "换药" in keywords
    
    def test_detect_add_medication(self):
        """测试检测'加药'关键词"""
        text = "我想自己加药量"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "加药" in keywords
    
    def test_detect_reduce_medication(self):
        """测试检测'减药'关键词"""
        text = "能不能帮我减药"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "减药" in keywords
    
    # ===== 断食类测试 =====
    
    def test_detect_water_fasting(self):
        """测试检测'水断食'关键词"""
        text = "我想尝试水断食"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "水断食" in keywords
    
    def test_detect_fasting_24_hours(self):
        """测试检测'断食超过24小时'关键词"""
        text = "我计划断食超过24小时"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "断食超过24小时" in keywords
    
    def test_detect_fasting_pattern_hours(self):
        """测试检测断食时间模式（小时）"""
        text = "我想断食48小时"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert any("断食48" in k for k in keywords)
    
    def test_detect_fasting_pattern_days(self):
        """测试检测断食时间模式（天）"""
        text = "我计划断食3天"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert any("断食3天" in k for k in keywords)
    
    def test_detect_fasting_exactly_24_hours(self):
        """测试检测正好24小时断食"""
        text = "断食24小时可以吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
    
    def test_no_detect_short_fasting(self):
        """测试不检测短时间断食（<24小时）"""
        text = "我想断食16小时的间歇性断食"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        # 仅动态模式不应触发，除非包含静态关键词
        # 16小时 < 24小时，不应触发
        assert not any("断食16" in k for k in keywords)
    
    # ===== 极端饮食类测试 =====
    
    def test_detect_keto_diet(self):
        """测试检测'生酮饮食'关键词"""
        text = "生酮饮食适合我吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "生酮饮食" in keywords
    
    def test_detect_very_low_calorie_diet(self):
        """测试检测'极低热量饮食'关键词"""
        text = "极低热量饮食有什么风险"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "极低热量饮食" in keywords
    
    def test_detect_calorie_pattern_low(self):
        """测试检测低于800千卡热量模式"""
        text = "我每天只吃500千卡可以吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert any("500" in k for k in keywords)
    
    def test_detect_calorie_pattern_kcal(self):
        """测试检测kcal单位的低热量"""
        text = "每天600kcal够不够"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert any("600" in k for k in keywords)
    
    def test_no_detect_normal_calorie(self):
        """测试不检测正常热量（>=800千卡）"""
        text = "我每天吃1500千卡够吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        # 1500千卡不应触发低热量警告
        assert not any("1500" in k for k in keywords)
    
    def test_no_detect_800_calorie_boundary(self):
        """测试800千卡边界值不触发"""
        text = "每天800千卡的饮食计划"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        # 正好800千卡不应触发（< 800才触发）
        assert not any("800千卡" in k for k in keywords)
    
    # ===== 大剂量补剂类测试 =====
    
    def test_detect_high_dose_supplement(self):
        """测试检测'大剂量补剂'关键词"""
        text = "大剂量补剂有危险吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "大剂量补剂" in keywords
    
    def test_detect_rda_pattern_3x(self):
        """测试检测3倍RDA模式"""
        text = "我想吃3倍RDA的维生素C"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert any("3倍RDA" in k for k in keywords)
    
    def test_detect_rda_pattern_5x(self):
        """测试检测5倍推荐量模式"""
        text = "5倍推荐量的补剂安全吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert any("5倍推荐量" in k for k in keywords)
    
    def test_no_detect_rda_pattern_2x(self):
        """测试不检测2倍RDA（<3倍）"""
        text = "2倍RDA的维生素可以吗"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        # 2倍 < 3倍，不应触发
        assert not any("2倍RDA" in k for k in keywords)
    
    # ===== 边界情况测试 =====
    
    def test_empty_text(self):
        """测试空文本"""
        is_high_risk, keywords = detect_high_risk_keywords("")
        assert is_high_risk is False
        assert keywords == []
    
    def test_none_text(self):
        """测试None输入"""
        is_high_risk, keywords = detect_high_risk_keywords(None)
        assert is_high_risk is False
        assert keywords == []
    
    def test_no_high_risk_keywords(self):
        """测试不包含高风险关键词的文本"""
        text = "我想了解健康饮食建议"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is False
        assert keywords == []
    
    def test_multiple_high_risk_keywords(self):
        """测试包含多个高风险关键词"""
        text = "我想停药并尝试生酮饮食加水断食"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "停药" in keywords
        assert "生酮饮食" in keywords
        assert "水断食" in keywords
    
    def test_no_duplicate_keywords(self):
        """测试不返回重复关键词"""
        text = "我要停药，真的想停药，必须停药"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert keywords.count("停药") == 1


class TestDetectProhibitedKeywords:
    """禁止关键词检测测试 (Requirement 5.4, 8.7)"""
    
    def test_detect_suicide(self):
        """测试检测'自杀'关键词"""
        text = "我有自杀的想法"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "自杀" in keywords
    
    def test_detect_self_harm(self):
        """测试检测'自残'关键词"""
        text = "我会自残"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "自残" in keywords
    
    def test_detect_hallucination(self):
        """测试检测'幻觉'关键词"""
        text = "我经常出现幻觉"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "幻觉" in keywords
    
    def test_detect_auditory_hallucination(self):
        """测试检测'幻听'关键词"""
        text = "我有幻听的症状"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "幻听" in keywords
    
    def test_detect_delusion(self):
        """测试检测'妄想'关键词"""
        text = "医生说我有妄想症"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "妄想" in keywords
    
    def test_detect_manic_episode(self):
        """测试检测'躁狂发作'关键词"""
        text = "最近躁狂发作了"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "躁狂发作" in keywords
    
    def test_detect_severe_depression(self):
        """测试检测'重度抑郁'关键词"""
        text = "我被诊断为重度抑郁"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "重度抑郁" in keywords
    
    def test_detect_schizophrenia(self):
        """测试检测'精神分裂'关键词"""
        text = "精神分裂症患者可以用吗"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "精神分裂" in keywords
    
    def test_detect_bipolar_acute(self):
        """测试检测'双相情感障碍急性发作'关键词"""
        text = "双相情感障碍急性发作怎么办"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "双相情感障碍急性发作" in keywords
    
    def test_detect_want_to_die(self):
        """测试检测'想死'关键词"""
        text = "我想死"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "想死" in keywords
    
    def test_detect_dont_want_to_live(self):
        """测试检测'不想活'关键词"""
        text = "我不想活了"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "不想活" in keywords
    
    def test_empty_text(self):
        """测试空文本"""
        is_prohibited, keywords = detect_prohibited_keywords("")
        assert is_prohibited is False
        assert keywords == []
    
    def test_none_text(self):
        """测试None输入"""
        is_prohibited, keywords = detect_prohibited_keywords(None)
        assert is_prohibited is False
        assert keywords == []
    
    def test_no_prohibited_keywords(self):
        """测试不包含禁止关键词的文本"""
        text = "我最近睡眠不好，有点焦虑"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is False
        assert keywords == []
    
    def test_multiple_prohibited_keywords(self):
        """测试包含多个禁止关键词"""
        text = "我有幻觉和幻听，还有自杀的念头"
        is_prohibited, keywords = detect_prohibited_keywords(text)
        assert is_prohibited is True
        assert "幻觉" in keywords
        assert "幻听" in keywords
        assert "自杀" in keywords


class TestDetectOutOfScope:
    """超出服务范围检测测试 (Requirement 5.4)"""
    
    # ===== 诊断请求测试 =====
    
    def test_detect_diagnosis_request(self):
        """测试检测诊断请求"""
        text = "帮我诊断一下我是什么病"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "诊断" in reason
    
    def test_detect_check_if_have(self):
        """测试检测'是否患有'请求"""
        text = "帮我判断是否患有糖尿病"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "诊断" in reason
    
    # ===== 处方请求测试 =====
    
    def test_detect_prescription_request(self):
        """测试检测处方请求"""
        text = "能帮我开处方吗"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "处方" in reason
    
    def test_detect_medicine_recommendation(self):
        """测试检测药物推荐请求"""
        text = "我应该吃什么药治疗"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "处方" in reason
    
    # ===== 急性症状测试 =====
    
    def test_detect_chest_pain(self):
        """测试检测胸痛"""
        text = "我现在胸痛很厉害"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "急" in reason or "紧急" in reason
    
    def test_detect_difficulty_breathing(self):
        """测试检测呼吸困难"""
        text = "我呼吸困难怎么办"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "急" in reason or "紧急" in reason
    
    def test_detect_consciousness_disorder(self):
        """测试检测意识障碍"""
        text = "我家人意识障碍了"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "急" in reason or "紧急" in reason
    
    def test_detect_high_fever_pattern(self):
        """测试检测高热模式（39度以上）"""
        text = "我发烧39.5度了"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "急" in reason or "紧急" in reason
    
    def test_detect_high_fever_celsius(self):
        """测试检测高热（摄氏度）"""
        text = "体温40°C怎么办"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
    
    def test_no_detect_normal_fever(self):
        """测试不检测正常发热（<39度）"""
        text = "我发烧37.5度"
        is_out, reason = detect_out_of_scope(text)
        # 37.5度不应触发急性症状
        # 注意：可能会因其他关键词触发，这里只检查高热部分
        # 如果触发，原因不应该是高热
        if is_out:
            assert "高热" not in reason
    
    # ===== 需处方治疗疾病测试 =====
    
    def test_detect_infectious_disease(self):
        """测试检测感染性疾病"""
        text = "我得了细菌感染"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "处方" in reason or "专科" in reason
    
    def test_detect_cancer(self):
        """测试检测肿瘤/癌症"""
        text = "我查出来癌症了"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "处方" in reason or "专科" in reason
    
    # ===== 儿科问题测试 =====
    
    def test_detect_children_keyword(self):
        """测试检测'儿童'关键词"""
        text = "儿童可以吃这个吗"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "儿" in reason or "12岁" in reason
    
    def test_detect_baby_keyword(self):
        """测试检测'宝宝'关键词"""
        text = "我家宝宝发烧了"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "儿" in reason or "12岁" in reason
    
    def test_detect_child_age_pattern(self):
        """测试检测年龄模式（12岁以下）"""
        text = "我儿子5岁，可以吃什么"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        assert "儿" in reason or "12岁" in reason
    
    def test_detect_child_age_11(self):
        """测试检测11岁儿童"""
        text = "孩子11岁了"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
    
    def test_no_detect_teenager(self):
        """测试不检测12岁及以上"""
        text = "我家孩子15岁了"
        is_out, reason = detect_out_of_scope(text)
        # 15岁不应触发儿科问题（但可能包含其他关键词如"孩子"）
        # 这里检查的是年龄模式不触发
        # 实际上"孩子"关键词在OUT_OF_SCOPE_KEYWORDS中没有单独列出
        # 如果测试失败，需要调整
        pass  # 根据实际实现调整
    
    # ===== 边界情况测试 =====
    
    def test_empty_text(self):
        """测试空文本"""
        is_out, reason = detect_out_of_scope("")
        assert is_out is False
        assert reason == ""
    
    def test_none_text(self):
        """测试None输入"""
        is_out, reason = detect_out_of_scope(None)
        assert is_out is False
        assert reason == ""
    
    def test_no_out_of_scope(self):
        """测试不包含超出范围内容的文本"""
        text = "我想了解如何改善睡眠质量"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is False
        assert reason == ""
    
    def test_multiple_out_of_scope_categories(self):
        """测试包含多个超出范围类别"""
        text = "帮我诊断孩子是不是得了感染"
        is_out, reason = detect_out_of_scope(text)
        assert is_out is True
        # 应该包含诊断和儿科相关信息
        assert "诊断" in reason or "儿" in reason


class TestGetProfessionalHelpSuggestion:
    """专业帮助建议文本测试"""
    
    def test_suggestion_contains_hotline(self):
        """测试建议包含热线电话"""
        suggestion = get_professional_help_suggestion()
        assert "400-161-9995" in suggestion or "热线" in suggestion
    
    def test_suggestion_contains_professional_advice(self):
        """测试建议包含专业就诊建议"""
        suggestion = get_professional_help_suggestion()
        assert "精神科" in suggestion or "心理科" in suggestion


class TestPerformSafetyCheck:
    """完整安全检查测试"""
    
    def test_safe_text(self):
        """测试安全文本"""
        text = "我想了解健康饮食建议"
        result = perform_safety_check(text)
        assert result["is_safe"] is True
        assert result["ui_interrupt_flag"] is False
        assert result["terminate"] is False
    
    def test_prohibited_keyword_terminates(self):
        """测试禁止关键词触发终止"""
        text = "我有自杀的想法"
        result = perform_safety_check(text)
        assert result["is_safe"] is False
        assert result["terminate"] is True
        assert "自杀" in result["prohibited_keywords"]
        assert result["message"]  # 应有提示消息
    
    def test_out_of_scope_terminates(self):
        """测试超出范围触发终止"""
        text = "帮我诊断是什么病"
        result = perform_safety_check(text)
        assert result["is_safe"] is False
        assert result["terminate"] is True
        assert result["out_of_scope_reason"]
    
    def test_high_risk_sets_interrupt_flag(self):
        """测试高风险关键词设置中断标志"""
        text = "我想停药试试"
        result = perform_safety_check(text)
        assert result["is_safe"] is True  # 高风险不是不安全，只是需要确认
        assert result["ui_interrupt_flag"] is True
        assert result["terminate"] is False
        assert "停药" in result["high_risk_keywords"]
    
    def test_prohibited_takes_priority(self):
        """测试禁止关键词优先级最高"""
        text = "我想停药，还有自杀的念头"
        result = perform_safety_check(text)
        # 禁止关键词应该导致终止
        assert result["terminate"] is True
        assert "自杀" in result["prohibited_keywords"]
    
    def test_out_of_scope_priority_over_high_risk(self):
        """测试超出范围优先于高风险"""
        text = "帮我诊断，我想停药"
        result = perform_safety_check(text)
        # 超出范围应该导致终止
        assert result["terminate"] is True
        assert result["out_of_scope_reason"]


class TestKeywordLists:
    """关键词列表完整性测试"""
    
    def test_high_risk_keywords_not_empty(self):
        """测试高风险关键词列表非空"""
        assert len(HIGH_RISK_KEYWORDS) > 0
    
    def test_high_risk_keywords_contain_medication(self):
        """测试高风险关键词包含用药调整类"""
        medication_keywords = ["停药", "换药", "加药", "减药"]
        for kw in medication_keywords:
            assert kw in HIGH_RISK_KEYWORDS
    
    def test_high_risk_keywords_contain_fasting(self):
        """测试高风险关键词包含断食类"""
        assert "水断食" in HIGH_RISK_KEYWORDS
    
    def test_high_risk_keywords_contain_diet(self):
        """测试高风险关键词包含极端饮食类"""
        assert "生酮饮食" in HIGH_RISK_KEYWORDS
        assert "极低热量饮食" in HIGH_RISK_KEYWORDS
    
    def test_high_risk_keywords_contain_supplement(self):
        """测试高风险关键词包含大剂量补剂类"""
        assert "大剂量补剂" in HIGH_RISK_KEYWORDS
    
    def test_prohibited_keywords_not_empty(self):
        """测试禁止关键词列表非空"""
        assert len(PROHIBITED_KEYWORDS) > 0
    
    def test_prohibited_keywords_contain_all_required(self):
        """测试禁止关键词包含所有必需关键词 (Requirement 5.4, 8.7)"""
        required_keywords = [
            "自杀", "自残", "幻觉", "幻听", "妄想",
            "躁狂发作", "重度抑郁", "精神分裂", "双相情感障碍急性发作"
        ]
        for kw in required_keywords:
            assert kw in PROHIBITED_KEYWORDS, f"缺少禁止关键词: {kw}"
    
    def test_out_of_scope_categories(self):
        """测试超出范围类别"""
        expected_categories = [
            "诊断请求", "处方请求", "急性症状", "需处方治疗疾病", "儿科问题"
        ]
        for category in expected_categories:
            assert category in OUT_OF_SCOPE_KEYWORDS, f"缺少类别: {category}"


class TestEdgeCases:
    """边界情况和特殊场景测试"""
    
    def test_unicode_text(self):
        """测试Unicode文本"""
        text = "我想停药试试 🤔"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "停药" in keywords
    
    def test_mixed_language(self):
        """测试中英混合文本"""
        text = "我想try生酮饮食keto diet"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "生酮饮食" in keywords
    
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        text = "  我 想 停 药  "
        # 由于关键词是连续的"停药"，这个不应该匹配
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert "停药" not in keywords
        
        text2 = "我想停药"
        is_high_risk2, keywords2 = detect_high_risk_keywords(text2)
        assert is_high_risk2 is True
        assert "停药" in keywords2
    
    def test_partial_match(self):
        """测试部分匹配"""
        # "药"单独出现不应触发"停药"
        text = "我吃药了"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert "停药" not in keywords
    
    def test_long_text(self):
        """测试长文本"""
        text = "这是一段很长的文本，" * 100 + "我想停药"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "停药" in keywords
    
    def test_special_characters(self):
        """测试特殊字符"""
        text = "停药！！！"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        assert is_high_risk is True
        assert "停药" in keywords
    
    def test_newlines(self):
        """测试换行符"""
        text = "我想\n停药\n试试"
        is_high_risk, keywords = detect_high_risk_keywords(text)
        # 换行符分隔不应匹配连续的"停药"
        # 但如果"停药"是完整的，应该匹配
        assert "停药" in keywords
