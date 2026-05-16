import React, { useState, useEffect } from 'react'
import { apiFetch } from '../core/api'
import { UserPlus, Edit3, Trash2, Shield, Power } from 'lucide-react'

interface UserData {
  id: number
  username: string
  is_active: boolean
}

export default function UsersModule({ token }: { token: string }) {
  const [users, setUsers] = useState<UserData[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserData | null>(null)
  const [formData, setFormData] = useState({ username: '', password: '', is_active: true })

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const data = await apiFetch('/users', token)
      setUsers(data)
    } catch (e) {
      console.error('Error fetching users:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingUser) {
        await apiFetch(`/users/${editingUser.id}`, token, {
          method: 'PUT',
          body: JSON.stringify(formData)
        })
      } else {
        await apiFetch('/users', token, {
          method: 'POST',
          body: JSON.stringify(formData)
        })
      }
      setIsModalOpen(false)
      setEditingUser(null)
      setFormData({ username: '', password: '', is_active: true })
      fetchUsers()
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    }
  }

  const toggleStatus = async (user: UserData) => {
    try {
      await apiFetch(`/users/${user.id}`, token, {
        method: 'PUT',
        body: JSON.stringify({ is_active: !user.is_active })
      })
      fetchUsers()
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar este usuario?')) return
    try {
      await apiFetch(`/users/${id}`, token, { method: 'DELETE' })
      fetchUsers()
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    }
  }

  const openEdit = (user: UserData) => {
    setEditingUser(user)
    setFormData({ username: user.username, password: '', is_active: user.is_active })
    setIsModalOpen(true)
  }

  return (
    <div className="view-container animate-in-up" style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <div className="view-header" style={{ marginBottom: '32px' }}>
        <div>
          <h2 className="view-title">Gestión de Usuarios</h2>
          <p className="view-subtitle">Administra los accesos y el estado de los usuarios del sistema</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setEditingUser(null); setFormData({ username: '', password: '', is_active: true }); setIsModalOpen(true); }}
          style={{ padding: '12px 24px', borderRadius: '12px', fontWeight: 600 }}>
          <UserPlus size={20} style={{ marginRight: '8px' }} />
          Nuevo Usuario
        </button>
      </div>

      <div className="kpi-card-v3 shadow-giant" style={{ padding: '0', borderRadius: '16px', border: '1px solid #eef2f6', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #eef2f6' }}>
              <th style={{ padding: '20px 24px', textAlign: 'left', color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Usuario</th>
              <th style={{ padding: '20px 24px', textAlign: 'center', color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Estado de Acceso</th>
              <th style={{ padding: '20px 24px', textAlign: 'right', color: '#64748b', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={3} style={{ textAlign: 'center', padding: '60px' }}>Cargando usuarios...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={3} style={{ textAlign: 'center', padding: '60px' }}>No hay usuarios registrados.</td></tr>
            ) : users.map(user => (
              <tr key={user.id} style={{ borderBottom: '1px solid #f8fafc' }}>
                <td style={{ padding: '20px 24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div className="user-avatar" style={{ width: '40px', height: '40px', background: '#f0f7ff', color: '#0284c7' }}>
                      {user.username[0].toUpperCase()}
                    </div>
                    <div style={{ fontWeight: 700, color: '#0f172a' }}>{user.username}</div>
                  </div>
                </td>
                <td style={{ padding: '20px 24px', textAlign: 'center' }}>
                  <button 
                    onClick={() => toggleStatus(user)}
                    style={{ 
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 16px',
                      borderRadius: '30px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      border: 'none',
                      background: user.is_active ? '#f0fdf4' : '#fff1f2',
                      color: user.is_active ? '#15803d' : '#e11d48',
                      transition: 'all 0.2s'
                    }}
                    title={user.is_active ? "Suspender Usuario" : "Activar Usuario"}
                  >
                    <Power size={14} />
                    {user.is_active ? 'ACTIVO' : 'INACTIVO'}
                  </button>
                </td>
                <td style={{ padding: '20px 24px', textAlign: 'right' }}>
                  <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                    <button className="btn-icon" onClick={() => openEdit(user)} style={{ background: '#f8fafc', color: '#64748b' }}>
                      <Edit3 size={18} />
                    </button>
                    <button className="btn-icon" onClick={() => handleDelete(user.id)} style={{ background: '#fff1f2', color: '#e11d48' }}>
                      <Trash2 size={18} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card animate-in-up" style={{ width: '400px' }}>
            <div className="modal-header">
              <h3 className="modal-title">{editingUser ? 'Editar Credenciales' : 'Nuevo Acceso'}</h3>
            </div>
            <form onSubmit={handleSubmit} style={{ padding: '24px' }}>
              <div className="form-group">
                <label className="form-label">Nombre de Usuario</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={formData.username}
                  onChange={e => setFormData({ ...formData, username: e.target.value })}
                  required
                />
              </div>
              <div className="form-group" style={{ marginTop: '16px' }}>
                <label className="form-label">{editingUser ? 'Nueva Contraseña' : 'Contraseña'}</label>
                <input 
                  type="password" 
                  className="form-input" 
                  value={formData.password}
                  onChange={e => setFormData({ ...formData, password: e.target.value })}
                  placeholder={editingUser ? "Dejar en blanco para mantener" : ""}
                  required={!editingUser}
                />
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '32px' }}>
                <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setIsModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>{editingUser ? 'Guardar' : 'Crear'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
