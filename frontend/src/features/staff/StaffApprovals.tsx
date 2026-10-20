import StudentApprovalQueue from '../students/StudentApprovalQueue.tsx'

export default function StaffApprovals({ accessToken, canApprove, canReject }: { accessToken: string; canApprove?: boolean; canReject?: boolean }) {
  return <StudentApprovalQueue key={accessToken} accessToken={accessToken} namespace="staff" canApprove={canApprove} canReject={canReject} />
}
