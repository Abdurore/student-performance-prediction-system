export interface AcademicHistoryItem {
  session: string
  semester: string
  credits_registered: number
  credits_earned: number
  gpa: number
  cgpa: number
  standing: string
}

export interface EnrolmentItem {
  course_code: string
  course_title: string
  session: string
  semester: string
  ca_score: number | null
  exam_score: number | null
  total_score: number | null
  grade: string | null
  attendance_rate: number | null
  status: string
}

export interface StudentProfile {
  id: number
  matric_no: string
  first_name: string
  last_name: string
  department: string
  programme: string
  level: number
  adviser_id: number | null
  is_active: boolean
  academic_history: AcademicHistoryItem[]
  enrolments: EnrolmentItem[]
}

export interface StudentListItem {
  id: number
  matric_no: string
  first_name: string
  last_name: string
  department: string
  level: number
  adviser_id: number | null
  is_active: boolean
  risk_tier: string | null
}

export interface PaginatedStudents {
  items: StudentListItem[]
  total: number
  page: number
  page_size: number
}

export interface Course {
  id: number
  course_code: string
  title: string
  credit_units: number
  level: number
  semester: string
  department: string
  lecturer_id: number | null
  is_core: boolean
}
