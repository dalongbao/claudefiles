# Job Search - Research Position Discovery Agent

Find ML/AI research positions, labs, and internship opportunities in specified regions.

**Usage**: `/user:job-search [regions] [focus_areas]`

**Examples**:
- `/user:job-search "China, Hong Kong, UK" "ML systems, LLM inference"`
- `/user:job-search "Singapore, Japan" "NLP, foundation models"`
- `/user:job-search "Europe" "distributed training, fault tolerance"`

## Implementation

Execute this job search using the Task tool to launch parallel research subagents:

### Phase 1: Regional Lab Discovery

Launch parallel subagents for each specified region:

```
For each region in $ARGUMENTS:

Task: "[Region] Research Lab Discovery"
- Prompt: "Search for ML/AI research labs and opportunities in [region]. Focus on:
  1. University labs with active internship programs
  2. Industry research labs (tech companies, AI startups)
  3. Government-funded research centers

  For each opportunity found, extract:
  - Lab/Group name and affiliation
  - Key researchers/professors and their research focus
  - Contact email or application portal
  - Current openings (PhD, intern, RA positions)
  - Research alignment with: [focus_areas]

  Use WebSearch to find current job postings and lab websites."
```

### Phase 2: Deep Dive on Promising Matches

For high-relevance matches, launch follow-up subagents:

```
Task: "Deep Profile Research"
- Prompt: "Research [researcher/lab name] in depth:
  1. Recent publications (last 2 years)
  2. Current projects and funding
  3. Lab culture and intern experiences (check Twitter/X, LinkedIn)
  4. Application requirements and deadlines
  5. Email template recommendations based on their work"
```

### Phase 3: Candidate Profile Matching

Cross-reference findings with candidate background:

**Candidate Profile** (customize as needed):
- ML systems experience (distributed training, inference/serving)
- LLM infrastructure work (vLLM, ServerlessLLM-related)
- Fault tolerance research
- Current: CS+AI undergraduate, ETH Zurich exchange

**Match Criteria**:
- Direct research overlap (weighted highest)
- Open positions for appropriate level
- Geographic/visa feasibility
- Application timeline alignment

## Output Format

```
=== JOB SEARCH RESULTS: [Regions] ===
Focus Areas: [focus_areas]
Search Date: [date]

---

## Tier 1: Strong Matches (Direct Research Overlap)

### [Lab/Researcher Name] — [Institution] ⭐⭐⭐

**Location:** [City, Country]
**Affiliation:** [University/Company]

**Research focus:**
- [Bullet points of relevant research]

**Why it's a match:**
- [Specific alignment with candidate profile]

**Current openings:** [Position types available]

**Application info:**
- **Contact:** [email]
- **Website:** [url]
- **Deadline:** [if known]
- **How to apply:** [specific instructions]

---

## Tier 2: Good Matches (Partial Overlap)

[Same format as Tier 1]

---

## Tier 3: Worth Considering

[Same format, briefer descriptions]

---

## Application Strategy

### Immediate Actions (This Week)
1. [Specific action items]

### Short-term (This Month)
1. [Action items]

### Upcoming Deadlines
| Position | Deadline | Priority |
|----------|----------|----------|
| ... | ... | ... |

---

## Email Templates

### For Academic Labs
```
Subject: [Suggested subject line]
[Template with personalization notes]
```

### For Industry Labs
```
Subject: [Suggested subject line]
[Template with personalization notes]
```
```

## Regional Search Strategies

### China (Mainland)
- Search: Tsinghua, Peking, SJTU, Zhejiang AI labs
- Industry: Alibaba DAMO, Tencent AI Lab, Baidu Research, ByteDance, SenseTime
- Platforms: zhipin.com, BOSS直聘 for industry; lab websites for academic

### Hong Kong
- Search: HKUST, CUHK, HKU, CityU, PolyU research groups
- Industry: MSRA (Beijing but recruits HK), Huawei Noah's Ark
- Programs: InnoHK centers, HKSTP

### United Kingdom
- Search: Cambridge, Oxford, Imperial, UCL, Edinburgh AI labs
- Industry: Google DeepMind, Meta AI London, Microsoft Research Cambridge
- Programs: UKRI CDTs, Alan Turing Institute

### Singapore
- Search: NUS, NTU, SUTD, A*STAR research institutes
- Industry: Google, Meta, ByteDance APAC offices

### Japan
- Search: University of Tokyo, Kyoto, RIKEN AIP
- Industry: Preferred Networks, Sony AI, LINE

## Success Criteria

- Comprehensive coverage of specified regions
- Accurate, current information (verify with web search)
- Clear prioritization based on research fit
- Actionable next steps with specific contacts
- Realistic assessment of opportunity competitiveness

Execute the job search for: $ARGUMENTS
