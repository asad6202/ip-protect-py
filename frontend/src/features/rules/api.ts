import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib-utils/api'
import { RuleSet, Rule, CreateRuleSetRequest, UpdateRuleSetRequest, CreateRuleRequest, UpdateRuleRequest } from '@/lib-utils/types'

// Rule Sets API
export function useListRuleSets() {
  return useQuery({
    queryKey: ['rule-sets'],
    queryFn: async (): Promise<RuleSet[]> => {
      const response = await api.get('/v1/rule_sets')
      return response.data
    },
  })
}

export function useGetRuleSet(id: string) {
  return useQuery({
    queryKey: ['rule-sets', id],
    queryFn: async (): Promise<RuleSet> => {
      const response = await api.get(`/v1/rule_sets/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useCreateRuleSet() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreateRuleSetRequest): Promise<RuleSet> => {
      const response = await api.post('/v1/rule_sets', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rule-sets'] })
    },
  })
}

export function useUpdateRuleSet() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateRuleSetRequest }): Promise<RuleSet> => {
      const response = await api.patch(`/v1/rule_sets/${id}`, data)
      return response.data
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['rule-sets'] })
      queryClient.invalidateQueries({ queryKey: ['rule-sets', id] })
    },
  })
}

export function useDeleteRuleSet() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/v1/rule_sets/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rule-sets'] })
    },
  })
}

// Rules API
export function useListRules(ruleSetId: string) {
  return useQuery({
    queryKey: ['rules', ruleSetId],
    queryFn: async (): Promise<Rule[]> => {
      const response = await api.get(`/v1/rule_sets/${ruleSetId}/rules`)
      return response.data
    },
    enabled: !!ruleSetId,
  })
}

export function useCreateRule() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreateRuleRequest): Promise<Rule> => {
      const response = await api.post('/v1/rules', data)
      return response.data
    },
    onSuccess: (_, data) => {
      queryClient.invalidateQueries({ queryKey: ['rules', data.rule_set_id] })
    },
  })
}

export function useUpdateRule() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, data, ruleSetId }: { id: string; data: UpdateRuleRequest; ruleSetId: string }): Promise<Rule> => {
      const response = await api.patch(`/v1/rules/${id}`, data)
      // Use ruleSetId to avoid unused parameter warning
      console.debug('Updating rule in rule set:', ruleSetId)
      return response.data
    },
    onSuccess: (_, { ruleSetId }) => {
      queryClient.invalidateQueries({ queryKey: ['rules', ruleSetId] })
    },
  })
}

export function useDeleteRule() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, ruleSetId }: { id: string; ruleSetId: string }): Promise<void> => {
      await api.delete(`/v1/rules/${id}`)
      // Use ruleSetId to avoid unused parameter warning
      console.debug('Deleting rule from rule set:', ruleSetId)
    },
    onSuccess: (_, { ruleSetId }) => {
      queryClient.invalidateQueries({ queryKey: ['rules', ruleSetId] })
    },
  })
}
