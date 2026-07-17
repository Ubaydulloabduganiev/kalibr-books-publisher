"use client";

import { useState } from "react";
import { KeyRound, Trash2, UserPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  changeUserPassword,
  createUser,
  deleteUser,
  listUsers,
  type UserOut,
} from "@/lib/api";
import type { Messages } from "@/lib/i18n";

type Props = { messages: Messages };

export function UserManager({ messages }: Props) {
  const t = messages.users;
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "editor">("editor");

  const [formStatus, setFormStatus] = useState<"idle" | "saving" | "ok" | "error">("idle");
  const [formMessage, setFormMessage] = useState<string | null>(null);

  const [pwUserId, setPwUserId] = useState<string | null>(null);
  const [pwValue, setPwValue] = useState("");
  const [pwStatus, setPwStatus] = useState<"idle" | "saving" | "ok" | "error">("idle");
  const [pwMessage, setPwMessage] = useState<string | null>(null);

  async function refresh() {
    const result = await listUsers();
    if (result.ok && result.data) {
      setUsers(result.data.users);
      setLoadError(null);
    } else {
      setLoadError(result.error ?? t.error);
    }
    setLoaded(true);
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!username.trim() || password.length < 8) return;
    setFormStatus("saving");
    setFormMessage(null);
    const result = await createUser({
      username: username.trim(),
      password,
      display_name: displayName.trim() || undefined,
      role,
    });
    if (result.ok && result.data) {
      setFormStatus("ok");
      setFormMessage(t.created);
      setUsername("");
      setDisplayName("");
      setPassword("");
      setRole("editor");
      await refresh();
    } else {
      setFormStatus("error");
      setFormMessage(result.error ?? t.error);
    }
  }

  async function handleChangePassword(user: UserOut) {
    if (pwValue.length < 8) {
      setPwStatus("error");
      setPwMessage(t.passwordTooShort);
      return;
    }
    setPwStatus("saving");
    setPwMessage(null);
    const result = await changeUserPassword(user.id, pwValue);
    if (result.ok) {
      setPwStatus("ok");
      setPwMessage(t.passwordChanged);
      setPwValue("");
      setPwUserId(null);
    } else {
      setPwStatus("error");
      setPwMessage(result.error ?? t.error);
    }
  }

  async function handleDelete(user: UserOut) {
    if (!confirm(t.confirmDelete.replace("{username}", user.username))) return;
    const result = await deleteUser(user.id);
    if (result.ok) {
      await refresh();
    } else {
      setLoadError(result.error ?? t.error);
    }
  }

  if (!loaded) {
    refresh();
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserPlus className="size-5 text-primary" aria-hidden="true" />
            {t.createTitle}
          </CardTitle>
          <CardDescription>{t.createDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm font-medium">{t.username}</label>
                <input
                  className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={t.usernamePlaceholder}
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">{t.displayName}</label>
                <input
                  className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder={t.displayNamePlaceholder}
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm font-medium">{t.password}</label>
                <input
                  type="password"
                  className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t.passwordPlaceholder}
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">{t.role}</label>
                <select
                  className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  value={role}
                  onChange={(e) => setRole(e.target.value as "admin" | "editor")}
                >
                  <option value="editor">{t.roleEditor}</option>
                  <option value="admin">{t.roleAdmin}</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={formStatus === "saving"}>
                {t.createButton}
              </Button>
              {formMessage && (
                <span
                  className={
                    formStatus === "ok" ? "text-sm text-success" : "text-sm text-danger"
                  }
                >
                  {formMessage}
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.listTitle}</CardTitle>
          <CardDescription>{t.listDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          {loadError && <p className="text-sm text-danger">{loadError}</p>}
          {!loadError && users.length === 0 && (
            <p className="text-sm text-muted-foreground">{t.empty}</p>
          )}
          <ul className="divide-y divide-border">
            {users.map((user) => (
              <li key={user.id} className="py-3">
                {pwUserId === user.id ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="password"
                      className="w-56 rounded border border-input bg-background px-3 py-2 text-sm"
                      value={pwValue}
                      onChange={(e) => setPwValue(e.target.value)}
                      placeholder={t.newPasswordPlaceholder}
                      autoFocus
                    />
                    <Button
                      size="sm"
                      onClick={() => handleChangePassword(user)}
                      disabled={pwStatus === "saving"}
                    >
                      {t.savePassword}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setPwUserId(null)}>
                      {t.cancel}
                    </Button>
                    {pwMessage && (
                      <span
                        className={
                          pwStatus === "ok" ? "text-sm text-success" : "text-sm text-danger"
                        }
                      >
                        {pwMessage}
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">
                        {user.display_name}{" "}
                        <span className="text-sm text-muted-foreground">@{user.username}</span>
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {user.role === "admin" ? t.roleAdmin : t.roleEditor}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setPwUserId(user.id);
                          setPwValue("");
                          setPwStatus("idle");
                          setPwMessage(null);
                        }}
                      >
                        <KeyRound className="size-4" aria-hidden="true" />
                        {t.changePassword}
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleDelete(user)}>
                        <Trash2 className="size-4" aria-hidden="true" />
                        {t.delete}
                      </Button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
