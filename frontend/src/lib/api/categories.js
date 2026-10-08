// Categories API client — read-only per docs/api-design.md §5.1 (issue #33
// ships only `GET /api/categories/`; create/update/delete are future work).
// Used by the expense form (#41) and, later, the budget form (#52/#53) to
// populate the category picker.
import { apiFetch } from "$lib/api";

/**
 * @returns {Promise<Array<{ id: number, user_id: number, name: string, description: string | null, is_active: boolean, created_at: string, updated_at: string }>>}
 */
export async function listCategories() {
  const data = await apiFetch("/api/categories/", { credentials: "include" });
  return data.categories;
}
