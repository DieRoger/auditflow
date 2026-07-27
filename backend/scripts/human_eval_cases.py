"""Human Evaluation — 10 个手工标注 Case + 评估脚本

每个 Case 包含:
  - 审计场景描述
  - 输入数据 (给 Agent)
  - Gold Standard (人工标注的正确答案)

Gold Standard 基于中国注册会计师审计准则 + 企业会计准则标注。
"""

HUMAN_CASES = [
    {
        "id": "H001",
        "description": "收入确认 — 年底突击销售",
        "scenario": "制造企业，12月签了三笔大合同共$12M，占Q4收入的40%。客户在正常信用期内，但发货集中在12月最后一周。行业平均Q4占比25%。",
        "input": {
            "audit_area": "Revenue Recognition",
            "financial_data": {
                "revenue_growth": "35%",
                "industry_avg": "8%",
                "q4_share": "40% of annual",
                "contracts_timing": "3 large deals in final week of Dec",
                "contract_value": "$12M",
                "industry_q4_avg": "25%",
            },
        },
        "gold": {
            "expected_risks": ["Premature Revenue Recognition", "Revenue Cutoff"],
            "severity": "HIGH",
            "reasoning": "年底突击销售可能导致收入提前确认，违反CAS 14收入确认五步法中'控制权转移'的判断标准。属于高风险领域。",
            "evidence_keywords": ["contract", "timing", "revenue recognition"],
        },
    },
    {
        "id": "H002",
        "description": "关联交易 — 非公允定价",
        "scenario": "上市公司向控股股东控制的子公司销售产品，售价低于市场价15%。同时向该子公司提供贷款$5M，利率2%远低于市场利率8%。",
        "input": {
            "audit_area": "Related Party Transactions",
            "financial_data": {
                "related_party_sales": "$30M at 15% below market",
                "related_party_loan": "$5M at 2% interest",
                "market_rate": "8%",
                "total_revenue": "$200M",
                "transaction_type": "Sales + Loan to controlling shareholder subsidiary",
            },
        },
        "gold": {
            "expected_risks": ["Related Party Transaction", "Transfer Pricing"],
            "severity": "HIGH",
            "reasoning": "关联交易定价非公允，可能涉及利益输送。CAS 36要求充分披露关联交易定价政策。属于高风险。",
            "evidence_keywords": ["related party", "pricing", "disclosure"],
        },
    },
    {
        "id": "H003",
        "description": "存货减值 — 技术迭代导致产品过时",
        "scenario": "电子制造企业，某产品线库存$120M，库龄14个月。行业技术更新率20%/年。该产品线收入同比下降15%。减值准备仅提了$2M（1.7%）。",
        "input": {
            "audit_area": "Inventory Valuation",
            "financial_data": {
                "inventory_value": "$120M",
                "obsolescence_reserve": "$2M (1.7%)",
                "avg_shelf_months": 14,
                "industry_tech_refresh": "20% annually",
                "revenue_decline": "15% in this product line",
            },
        },
        "gold": {
            "expected_risks": ["Inventory Obsolescence", "Inventory Impairment"],
            "severity": "MEDIUM",
            "reasoning": "库龄较长且技术迭代快，存在减值风险。但收入仅下降15%而非完全停滞，属于中等风险。CAS 1要求按成本与可变现净值孰低计量。",
            "evidence_keywords": ["obsolescence", "inventory", "reserve"],
        },
    },
    {
        "id": "H004",
        "description": "商誉减值 — 收购业务持续不达标",
        "scenario": "公司3年前收购一家企业产生商誉$50M。收购时预测收入增长20%，实际连续3年仅达预测的60%。所在行业市场萎缩25%。",
        "input": {
            "audit_area": "Goodwill Impairment",
            "financial_data": {
                "goodwill_value": "$50M",
                "acquisition_year": "2021",
                "projected_vs_actual": "60% for 3 consecutive years",
                "market_decline": "25% in segment",
                "planned_restructuring": "Yes — plant closure announced",
            },
        },
        "gold": {
            "expected_risks": ["Goodwill Impairment", "Impairment"],
            "severity": "HIGH",
            "reasoning": "连续3年不达标+行业萎缩+计划重组，存在明确减值迹象。CAS 8要求每年进行减值测试。属于高风险。",
            "evidence_keywords": ["goodwill", "impairment", "cash generating unit"],
        },
    },
    {
        "id": "H005",
        "description": "收入确认 — 合同修改的累积追补调整",
        "scenario": "软件公司，年底与客户修改了3份合同条款，新增服务内容。公司采用累积追补法调整了$12M收入，占Q3/Q4收入的8%。修改发生在报告期末最后一周。",
        "input": {
            "audit_area": "Revenue Recognition",
            "financial_data": {
                "contract_modifications": "3 contracts modified in final week",
                "modification_method": "Cumulative catch-up",
                "revenue_impact": "$12M (8% of H2 revenue)",
                "modification_timing": "Last week of reporting period",
                "client_industry": "Software/SaaS",
            },
        },
        "gold": {
            "expected_risks": ["Revenue Recognition", "Contract Modifications"],
            "severity": "HIGH",
            "reasoning": "期末大额合同修改采用累积追补法，需要判断修改是否构成单独履约义务。CAS 14要求区分合同修改类型。时间点敏感，高风险的盈余管理信号。",
            "evidence_keywords": ["contract modification", "cumulative catch-up", "performance obligation"],
        },
    },
    {
        "id": "H006",
        "description": "应收账款 — 期后大客户破产",
        "scenario": "公司应收账款$280M。资产负债表日后一个月，某大客户（应收$35M，占12.5%）申请破产。公司计提坏账$1.5M（仅4.3%），行业平均坏账率2.1%。",
        "input": {
            "audit_area": "Accounts Receivable",
            "financial_data": {
                "total_receivables": "$280M",
                "major_customer_receivable": "$35M (12.5%)",
                "customer_status": "Filed bankruptcy on Jan 15 (post year-end)",
                "allowance_for_doubtful": "$1.5M (4.3% of at-risk)",
                "industry_default_rate": "2.1%",
            },
        },
        "gold": {
            "expected_risks": ["Receivable Impairment", "Accounts Receivable"],
            "severity": "HIGH",
            "reasoning": "期后事项表明应收款可回收性存疑。计提比例仅4.3%远低于100%，坏账准备明显不足。CAS 22要求按预期信用损失模型计提。高风险。",
            "evidence_keywords": ["receivable", "allowance", "subsequent event"],
        },
    },
    {
        "id": "H007",
        "description": "固定资产减值 — 产能利用率持续下降",
        "scenario": "制造企业，固定资产原值$500M（主要是专用设备）。产能利用率从80%降至55%，且公司计划6个月内关闭其中一家工厂（涉及资产$40M）。",
        "input": {
            "audit_area": "Fixed Asset Valuation",
            "financial_data": {
                "fixed_asset_value": "$500M",
                "capacity_utilization": "55% (down from 80% 2 years ago)",
                "planned_closure": "One plant in 6 months (asset value $40M)",
                "industry_outlook": "Declining domestic demand",
            },
        },
        "gold": {
            "expected_risks": ["Asset Impairment", "Fixed Asset Impairment"],
            "severity": "MEDIUM",
            "reasoning": "产能利用率持续下降且计划关厂，存在减值迹象。但$40M关厂计划仅占总资产8%，整体影响有限。CAS 8要求对存在减值迹象的资产进行减值测试。中等风险。",
            "evidence_keywords": ["impairment", "fixed asset", "capacity"],
        },
    },
    {
        "id": "H008",
        "description": "或有负债 — 重大诉讼未充分披露",
        "scenario": "公司被起诉专利侵权，索赔金额$100M（占净资产60%）。法律意见认为'结果可能不利'。公司在财报中仅作为或有事项披露，未计提预计负债。",
        "input": {
            "audit_area": "Contingent Liabilities",
            "financial_data": {
                "lawsuit_type": "Patent infringement",
                "claimed_amount": "$100M (60% of net assets)",
                "legal_opinion": "Reasonably possible unfavorable outcome",
                "current_disclosure": "Contingent liability only, no provision",
                "company_revenue": "$850M",
                "net_income": "$85M",
            },
        },
        "gold": {
            "expected_risks": ["Contingent Liability", "Litigation"],
            "severity": "HIGH",
            "reasoning": "索赔金额重大（占净资产60%），法律意见'可能不利'。CAS 13要求对很可能导致经济利益流出的或有事项计提预计负债。当前仅披露不充分。高风险。",
            "evidence_keywords": ["contingent liability", "lawsuit", "disclosure"],
        },
    },
    {
        "id": "H009",
        "description": "收入确认 — 捆绑销售中的VSOE",
        "scenario": "通信设备企业，销售硬件+多年服务合同。硬件售价$100K，服务费$30K/年×3年=$90K。公司按合同总额$190K一次性确认收入。未单独确定硬件和服务的公允价值（VSOE）。",
        "input": {
            "audit_area": "Revenue Recognition",
            "financial_data": {
                "contract_type": "Hardware + 3-year maintenance bundled",
                "hardware_price": "$100K",
                "service_fee": "$30K/year for 3 years = $90K",
                "recognition_method": "Recognized $190K upfront",
                "vsoe": "Not established for either element",
                "industry": "Telecommunications equipment",
            },
        },
        "gold": {
            "expected_risks": ["Revenue Recognition", "Multiple Element Arrangement"],
            "severity": "HIGH",
            "reasoning": "捆绑合同未单独确定各履约义务的公允价值（VSOE），一次性确认全部收入违反CAS 14关于'识别履约义务'和'分摊交易价格'的要求。高风险。",
            "evidence_keywords": ["bundled", "vsoe", "performance obligation", "allocation"],
        },
    },
    {
        "id": "H010",
        "description": "持续经营 — 流动性危机",
        "scenario": "公司流动比率0.8（行业平均1.5），有$50M债务将于6个月内到期，但账面现金仅$10M。公司未获得新的融资安排，且正与银行协商展期但无明确结果。",
        "input": {
            "audit_area": "Going Concern",
            "financial_data": {
                "current_ratio": "0.8 (industry avg: 1.5)",
                "debt_due": "$50M within 6 months",
                "cash_on_hand": "$10M",
                "refinancing_status": "Negotiating with bank, no agreement",
                "operating_losses": "3 consecutive years of losses ($15M/year)",
            },
        },
        "gold": {
            "expected_risks": ["Going Concern", "Liquidity Risk"],
            "severity": "HIGH",
            "reasoning": "流动比率低于1，短期债务远超现金，无确定融资安排，持续亏损。CAS 30要求管理层评估持续经营能力。ISA 570要求在存在重大疑虑时修改审计意见。高风险。",
            "evidence_keywords": ["going concern", "liquidity", "debt covenant"],
        },
    },
]
