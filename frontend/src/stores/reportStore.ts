import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface Report {
  id: string;
  title: string;
  projectType: string;
  status: 'analysis' | 'writing' | 'review' | 'completed' | 'paused';
  progress: number;
  createdAt: string;
  updatedAt: string;
}

interface ReportStore {
  // 状态
  reports: Report[];
  currentSession: string | null;
  currentReport: Report | null;
  reportContent: string | null;
  isLoading: boolean;
  error: string | null;

  // 操作
  setReports: (reports: Report[]) => void;
  setCurrentSession: (sessionId: string | null) => void;
  setCurrentReport: (report: Report | null) => void;
  setReportContent: (content: string | null) => void;
  updateReportProgress: (sessionId: string, progress: number) => void;
  updateReportStatus: (sessionId: string, status: Report['status']) => void;
  createNewReport: (projectInfo: any) => Promise<string>;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useReportStore = create<ReportStore>()(
  devtools(
    (set, get) => ({
      // 初始状态
      reports: [
        {
          id: 'demo-1',
          title: '洛阳市数字化产业园项目绩效评估报告',
          projectType: '绩效评价',
          status: 'completed',
          progress: 100,
          createdAt: new Date(Date.now() - 86400000).toISOString(), // 1天前
          updatedAt: new Date(Date.now() - 3600000).toISOString(), // 1小时前
        },
        {
          id: 'demo-2',
          title: '城市基础设施建设项目评价',
          projectType: '基础设施',
          status: 'analysis',
          progress: 25,
          createdAt: new Date(Date.now() - 7200000).toISOString(), // 2小时前
          updatedAt: new Date(Date.now() - 1800000).toISOString(), // 30分钟前
        }
      ],
      currentSession: null,
      currentReport: null,
      reportContent: null,
      isLoading: false,
      error: null,

      // 操作方法
      setReports: (reports) => set({ reports }),
      
      setCurrentSession: (sessionId) => {
        const report = sessionId ? get().reports.find(r => r.id === sessionId) : null;
        set({ 
          currentSession: sessionId, 
          currentReport: report,
          // 如果是演示报告，设置示例内容；其他报告初始为null，等待WebSocket更新
          reportContent: report?.id === 'demo-1' ? getDemoReportContent() : null
        });
      },
      
      setCurrentReport: (report) => set({ currentReport: report }),
      
      setReportContent: (content) => set({ reportContent: content }),
      
      updateReportProgress: (sessionId, progress) => {
        set((state) => ({
          reports: state.reports.map(report =>
            report.id === sessionId
              ? { ...report, progress, updatedAt: new Date().toISOString() }
              : report
          ),
          currentReport: state.currentReport?.id === sessionId
            ? { ...state.currentReport, progress, updatedAt: new Date().toISOString() }
            : state.currentReport
        }));
      },
      
      updateReportStatus: (sessionId, status) => {
        set((state) => ({
          reports: state.reports.map(report =>
            report.id === sessionId
              ? { ...report, status, updatedAt: new Date().toISOString() }
              : report
          ),
          currentReport: state.currentReport?.id === sessionId
            ? { ...state.currentReport, status, updatedAt: new Date().toISOString() }
            : state.currentReport
        }));
      },
      
      createNewReport: async (projectInfo) => {
        set({ isLoading: true, error: null });
        
        try {
          // 调用后端API创建新会话
          const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(projectInfo),
          });
          
          if (!response.ok) {
            throw new Error('创建会话失败');
          }
          
          const { session_id } = await response.json();
          
          // 创建新报告记录
          const newReport: Report = {
            id: session_id,
            title: projectInfo.name || '新建报告',
            projectType: projectInfo.type || '绩效评价',
            status: 'analysis',
            progress: 0,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
          
          set((state) => ({
            reports: [newReport, ...state.reports],
            isLoading: false,
          }));
          
          return session_id;
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : '创建报告失败',
            isLoading: false 
          });
          throw error;
        }
      },
      
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'report-store',
    }
  )
);

// 演示报告内容
function getDemoReportContent(): string {
  return `# 洛阳市数字化产业园项目绩效评估报告

## 报告摘要

本报告对洛阳市数字化产业园项目进行了全面的绩效评价。通过构建科学的评价指标体系，运用定量与定性相结合的方法，对项目的决策、过程、产出和效益进行了深入分析。

**主要结论**：项目整体绩效良好，达到了预期目标，在推动区域数字经济发展方面发挥了重要作用。

## 目录

1. 基本情况
2. 评价结论和绩效分析  
3. 主要成效、存在的问题及原因分析
4. 工作建议
5. 其他需要说明的问题
6. 附件

## 一、基本情况

### （一）项目背景和目的

洛阳市数字化产业园项目是在国家数字经济发展战略指导下启动的重要项目。项目旨在打造区域数字经济发展高地，推动传统产业数字化转型，培育新兴数字产业，具有重要的战略意义。

### （二）资金安排和使用情况

- **项目总预算**：5000万元
- **资金来源**：财政资金3000万元，社会投资2000万元
- **使用情况**：截至评价时点，已使用资金4500万元，使用率90%，资金使用合规

### （三）项目的组织及管理

项目建立了完善的组织管理体系，成立了项目领导小组，明确了各方职责，建立了有效的沟通协调机制。

## 二、评价结论和绩效分析

### （一）总体结论

基于构建的指标体系，项目综合得分为88分，评价等级为"良好"。

### （二）绩效分析

#### 决策指标分析（25分，得分22分）
- **立项依据充分性**：项目立项依据充分，符合国家和地方政策导向
- **目标设定合理性**：目标设定基本合理，具有可操作性，但部分指标略显乐观

#### 过程指标分析（30分，得分26分）  
- **实施进度达成率**：项目实施进度基本按计划推进，完成率85%
- **资金使用合规性**：资金使用规范，符合财务管理要求
- **管理制度完善性**：建立了较为完善的管理制度体系

#### 产出指标分析（25分，得分22分）
- **预期成果完成度**：主要成果基本实现，完成度80%
- **质量标准符合度**：产出质量总体符合要求，达到预期标准

#### 效益指标分析（20分，得分18分）
- **经济效益实现度**：带动相关产业产值增长15%，经济效益初步显现
- **社会效益影响度**：提供就业岗位500个，社会效益积极正面
- **可持续发展贡献度**：为区域数字经济发展奠定了基础

## 三、主要成效、存在的问题及原因分析

### （一）主要成效

1. **产业集聚效应显著**
   - 引进数字经济企业50家
   - 形成了较为完整的产业链条
   - 产业集聚度不断提升

2. **创新能力持续增强**
   - 建立了3个技术创新平台
   - 申请专利120项，其中发明专利40项
   - 产学研合作不断深化

3. **基础设施日趋完善**
   - 建成高标准数据中心1个
   - 5G网络覆盖率达到95%
   - 智能化办公环境基本形成

### （二）存在的问题及原因分析

1. **高端人才相对不足**
   - **问题表现**：缺乏行业领军人才和高端技术人才
   - **原因分析**：人才政策吸引力有限，薪酬待遇竞争力不强
   - **影响程度**：制约了产业高质量发展

2. **产业链协同有待加强**
   - **问题表现**：企业间协作不够紧密，产业链条存在断点
   - **原因分析**：缺乏有效的协调机制，企业各自为政
   - **影响程度**：影响了整体竞争力的提升

## 四、工作建议

### （一）完善人才引育体系
1. **加大人才引进力度**
   - 制定更具竞争力的人才政策
   - 提供更优质的生活配套服务
   - 建立人才发展基金

2. **强化人才培养机制**
   - 与高校建立人才培养合作关系
   - 开展在职人员技能提升培训
   - 建立人才梯队培养体系

### （二）优化产业生态环境
1. **建立产业协同机制**
   - 成立产业联盟组织
   - 定期举办产业交流活动
   - 建立信息共享平台

2. **完善配套服务体系**
   - 提供一站式政务服务
   - 建立专业化服务机构
   - 优化营商环境

### （三）强化项目监管评估
1. **建立动态监测机制**
   - 完善项目监测指标体系
   - 建立定期评估制度
   - 及时发现和解决问题

2. **加强绩效管理**
   - 建立绩效考核体系
   - 强化结果运用
   - 持续改进提升

## 五、其他需要说明的问题

1. **数据获取限制**：部分企业经营数据获取困难，可能影响评价的全面性
2. **时效性考虑**：本次评价基于现有资料和数据，部分信息可能存在时效性问题
3. **外部环境影响**：疫情等外部因素对项目实施产生了一定影响

## 六、附件

1. 评价指标体系详表
2. 数据收集清单  
3. 相关政策文件汇编
4. 企业调研问卷及结果
5. 专家评议意见汇总

---

**评价机构**：洛阳智评咨询有限公司  
**项目负责人**：张三  
**报告日期**：2025年1月19日`;
}