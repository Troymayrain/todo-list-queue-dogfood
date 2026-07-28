# Ticket

实现选中的 Ticket 并满足其验收标准。

提交前，必须读取 `.sandcastle/config.json`，在 Agent sandbox 的当前 worktree 中依次执行 `commands.test` 与 `commands.verification` 的全部命令；遇到失败时定位并修复实现或不正确的测试，然后重新执行，全部通过后才能提交。测试必须覆盖 Ticket 的外部可观察行为，不得为了通过而删除、跳过或削弱验收断言。`commands.bootstrap` 由可信 Host 负责，不要在 Agent sandbox 中重复执行。

结束前，创建恰好一个以当前 HEAD 为父提交的 commit，并保持 worktree clean。不要添加 `Sandcastle-*` trailers；可信 Host 会在验证 commit 后添加发布元数据。不要 push，也不要修改 GitHub Issues 或 pull requests。
