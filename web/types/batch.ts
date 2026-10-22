import { SummaryData } from "@/types/batch_summary";

export interface BatchResult {
  summary: SummaryData;
  batch_shap_bar: string;
  batch_shap_beeswarm: string;
  file_id: string;
}
