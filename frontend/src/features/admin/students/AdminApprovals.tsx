import StudentApprovalQueue from '../../students/StudentApprovalQueue.tsx'

export default function AdminApprovals({ accessToken }: { accessToken: string }) {
  return <StudentApprovalQueue key={accessToken} accessToken={accessToken} namespace="admin" />
}
