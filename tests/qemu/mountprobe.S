.global _start
.text
_start:
 mov (%rsp),%rax
 cmp $2,%rax
 je sync_it
 cmp $3,%rax
 je unmount_it
 mov 16(%rsp),%rdi
 mov 24(%rsp),%rsi
 mov 32(%rsp),%rdx
 xor %r10d,%r10d
 xor %r8d,%r8d
 mov $165,%eax
 syscall
 jmp done
unmount_it:
 mov 24(%rsp),%rdi
 xor %esi,%esi
 mov $166,%eax
 syscall
 jmp done
sync_it:
 mov $162,%eax
 syscall
done:
 neg %rax
 mov %rax,%rdi
 mov $60,%eax
 syscall
