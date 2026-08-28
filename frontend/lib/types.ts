export type Language = "en" | "hi" | "bn";
export type Confidence = "high" | "medium" | "low";

export interface SourceRef {
  standard_number: string | null;
  title: string | null;
  document_type: string;
  clause: string | null;
  section: string | null;
  page: number | null;
  source: string;
  source_url: string | null;
  chunk_id: string | null;
  excerpt: string | null;
  score: number;
}

export interface Standard {
  id: string;
  standard_number: string;
  title: string;
  scope: string;
  category: string;
  industry: string;
  edition: string;
  publication_date: string;
  status: string;
  keywords: string[];
  materials: string[];
  intended_use: string[];
  related_standards: string[];
  certification_required: boolean | null;
  certification_scheme: string | null;
  testing_summary: string;
  source_url: string | null;
  summary_hi?: string | null;
  summary_bn?: string | null;
  demo: boolean;
}

export interface StandardMatch {
  standard: Standard;
  relevance: number;
  reasons: string[];
  match_factors: Record<string, boolean>;
  sources: SourceRef[];
}

export interface Laboratory {
  id: string;
  name: string;
  city: string;
  state: string;
  lab_type: string;
  recognition_status: string;
  recognition_scope: string[];
  testing_capabilities: string[];
  product_categories: string[];
  standards_covered: string[];
  contact: string;
  email: string;
  source_url: string | null;
  demo: boolean;
}

export interface CertificationScheme {
  id: string;
  scheme_name: string;
  short_name: string;
  product_category: string;
  applies_to: string[];
  standard_numbers: string[];
  mandatory: boolean;
  requirements: string[];
  documents: string[];
  procedure: string[];
  testing: string[];
  inspection: string;
  typical_timeline: string;
  source_url: string | null;
  demo: boolean;
}

export interface HallmarkingTopic {
  id: string;
  topic: string;
  category: string;
  summary: string;
  details: string[];
  source_url: string | null;
  demo: boolean;
}

export interface ProductUnderstanding {
  product: string;
  category: string;
  materials: string[];
  intended_use: string;
  industry: string;
  target_user: string;
  characteristics: string[];
  notes: string;
}

export interface CertificationInfo {
  required: string;
  scheme: string | null;
  process: string[];
  documents: string[];
  inspection: string | null;
  verified: boolean;
}

export interface TestingInfo {
  tests: string[];
  laboratory_category: string | null;
  laboratories: Laboratory[];
  verified: boolean;
}

export interface AssistantAnswer {
  answer: string;
  intent: string;
  language: Language;
  product_understanding: ProductUnderstanding | null;
  standards: StandardMatch[];
  why_match: string[];
  certification: CertificationInfo | null;
  testing: TestingInfo | null;
  documents: string[];
  next_steps: string[];
  sources: SourceRef[];
  confidence: Confidence;
  confidence_score: number;
  evidence_found: boolean;
  generator: string;
  guardrail_notes: string[];
  disclaimer: string;
}

export interface ComplianceItem {
  id: string;
  label: string;
  detail: string;
  completed: boolean;
  source: SourceRef | null;
}

export interface ComplianceChecklist {
  product: string;
  standard_number: string | null;
  items: ComplianceItem[];
  completed: number;
  total: number;
  generated_at: string;
  sources: SourceRef[];
}

export interface CompareResponse {
  standards: Standard[];
  rows: { parameter: string; values: Record<string, string> }[];
  sources: SourceRef[];
}

export interface Meta {
  app: string;
  version: string;
  demo_mode: boolean;
  demo_notice: string;
  llm_enabled: boolean;
  generator: string;
  languages: { code: Language; label: string }[];
  standards: number;
  indexed_chunks: number;
  documents: number;
  certification_schemes: number;
  laboratories: number;
  hallmarking_topics: number;
  last_updated: string | null;
  storage_driver: string;
  embedding_provider: string;
}
