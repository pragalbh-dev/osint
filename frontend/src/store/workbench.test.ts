import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import type { AskAnswer, AskRequest } from '@/api/types'
import { useWorkbench } from './workbench'

// The store's runAsk POSTs through api.ask — mock the client so we can both control the
// response and inspect the request body (the `history` it carries). Only `ask` is exercised
// here; the rest of the client is stubbed enough to import cleanly.
vi.mock('@/api/client', () => ({
  api: { ask: vi.fn() },
  ApiError: class ApiError extends Error {},
}))

const askMock = api.ask as unknown as ReturnType<typeof vi.fn>

/** An answered turn (prose present). */
const answered = (question: string, answer: string): AskAnswer => ({ question, answer })
/** A refused turn (answer null — nothing to carry into history). */
const refused = (question: string): AskAnswer => ({
  question,
  answer: null,
  refusal: { kind: 'evidence', missing: ['a second look'] },
})

/** The history array sent with the Nth (0-based) api.ask call. */
const historyOf = (call: number): AskRequest['history'] =>
  (askMock.mock.calls[call][0] as AskRequest).history

beforeEach(() => {
  askMock.mockReset()
  useWorkbench.setState({
    mode: 'live',
    askTurns: [],
    askQuestion: '',
    askPending: false,
    askError: false,
    panelView: 'zero',
  })
})

describe('runAsk — chat thread', () => {
  it("first question sends an empty history and appends the turn", async () => {
    askMock.mockResolvedValueOnce(answered('Where is the battery?', 'It is at Rahwali [c1].'))

    await useWorkbench.getState().runAsk('Where is the battery?')

    expect(historyOf(0)).toEqual([])
    const s = useWorkbench.getState()
    expect(s.askTurns).toHaveLength(1)
    expect(s.askTurns[0].question).toBe('Where is the battery?')
    expect(s.askTurns[0].answer.answer).toBe('It is at Rahwali [c1].')
    expect(s.askPending).toBe(false)
    expect(s.panelView).toBe('answer')
  })

  it('a follow-up carries the prior turns as history (raw answer text)', async () => {
    askMock.mockResolvedValueOnce(answered('Q1', 'Answer one.'))
    await useWorkbench.getState().runAsk('Q1')

    askMock.mockResolvedValueOnce(answered('Q2', 'Answer two.'))
    await useWorkbench.getState().runAsk('Q2')

    expect(historyOf(1)).toEqual([{ question: 'Q1', answer: 'Answer one.' }])
    expect(useWorkbench.getState().askTurns.map((t) => t.question)).toEqual(['Q1', 'Q2'])
  })

  it('a refused prior turn contributes answer: null to history', async () => {
    askMock.mockResolvedValueOnce(refused('Q1'))
    await useWorkbench.getState().runAsk('Q1')

    askMock.mockResolvedValueOnce(answered('Q2', 'Answer two.'))
    await useWorkbench.getState().runAsk('Q2')

    expect(historyOf(1)).toEqual([{ question: 'Q1', answer: null }])
    // the refused turn is still a turn in the transcript
    expect(useWorkbench.getState().askTurns).toHaveLength(2)
  })

  it('trims whitespace and ignores an empty question', async () => {
    await useWorkbench.getState().runAsk('   ')
    expect(askMock).not.toHaveBeenCalled()

    askMock.mockResolvedValueOnce(answered('Q1', 'A.'))
    await useWorkbench.getState().runAsk('  Q1  ')
    expect((askMock.mock.calls[0][0] as AskRequest).question).toBe('Q1')
    expect(useWorkbench.getState().askTurns[0].question).toBe('Q1')
  })

  it('a transport failure sets askError without appending a turn', async () => {
    askMock.mockRejectedValueOnce(new Error('network'))
    await useWorkbench.getState().runAsk('Q1')

    const s = useWorkbench.getState()
    expect(s.askError).toBe(true)
    expect(s.askPending).toBe(false)
    expect(s.askTurns).toHaveLength(0)
  })

  it('is a no-op in demo mode (the demo never fetches)', async () => {
    useWorkbench.setState({ mode: 'demo' })
    await useWorkbench.getState().runAsk('Q1')
    expect(askMock).not.toHaveBeenCalled()
    expect(useWorkbench.getState().askTurns).toHaveLength(0)
  })
})

describe('newThread', () => {
  it('clears the transcript and returns to the empty zero state', async () => {
    askMock.mockResolvedValueOnce(answered('Q1', 'A.'))
    await useWorkbench.getState().runAsk('Q1')
    expect(useWorkbench.getState().askTurns).toHaveLength(1)

    useWorkbench.getState().newThread()

    const s = useWorkbench.getState()
    expect(s.askTurns).toEqual([])
    expect(s.askQuestion).toBe('')
    expect(s.askPending).toBe(false)
    expect(s.askError).toBe(false)
    expect(s.panelView).toBe('zero')
  })
})
