var e = 1024, t = 2048, n = 4096, r = 8192, i = 32768, a = 1 << 25, o = 65536, s = 1 << 19, c = 1 << 20, l = 1 << 25, u = 1 << 21, d = 1 << 22, f = 1 << 23, p = 1 << 27, m = 1 << 26, h = Symbol("$state"), g = Symbol("component"), ee = Symbol("legacy props"), _ = Symbol(""), te = Symbol("attributes"), v = Symbol("class"), ne = Symbol("style"), re = Symbol("text"), ie = Symbol("form reset"), ae = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), oe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), se = {}, y = Symbol("uninitialized");
function ce() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function le(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function ue() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var b = !1;
function x(e) {
	b = e;
}
var S;
function C(e) {
	if (e === null) throw le(), se;
	return S = e;
}
function de() {
	return C(/* @__PURE__ */ Pr(S));
}
function w(e) {
	if (b) {
		if (/* @__PURE__ */ Pr(S) !== null) throw le(), se;
		S = e;
	}
}
function fe(e = 1) {
	if (b) {
		for (var t = e, n = S; t--;) n = /* @__PURE__ */ Pr(n);
		S = n;
	}
}
function pe(e = !0) {
	for (var t = 0, n = S;;) {
		if (Wr(n) === 8) {
			var r = ti(n) ?? "";
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ Pr(n);
		e && Zr(n), n = i;
	}
}
function me(e) {
	if (!e || Wr(e) !== 8) throw le(), se;
	return ti(e) ?? "";
}
// node_modules/svelte/src/internal/shared/utils.js
var he = Array.isArray, ge = Array.prototype.indexOf, _e = Array.prototype.includes, ve = Array.from, ye = Object.keys, be = Object.defineProperty, xe = Object.getOwnPropertyDescriptor, Se = Object.getOwnPropertyDescriptors, Ce = Object.prototype, we = Array.prototype, Te = Object.getPrototypeOf, Ee = Object.isExtensible, De = () => {};
function Oe(e) {
	return e();
}
function ke(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function Ae() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function je(e) {
	var t = V;
	if (t === null) return e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	T(e, t);
}
function T(e, t) {
	if (e === se) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
function Me(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
function Ne(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Pe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Fe(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Ie() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Le() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Re(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function ze() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Be() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function He() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/flags/index.js
var Ue = !1;
function We() {
	Ue = !0;
}
// node_modules/svelte/src/internal/client/context.js
var E = null;
function Ge(e) {
	E = e;
}
function Ke(e, t = !1, n) {
	E = {
		p: E,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: V,
		l: Ue && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function qe(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) ln(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, Je(e);
}
function Je(e = {}) {
	return be(e, g, { value: !0 }), e;
}
function Ye() {
	return !Ue || E !== null && E.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], ke(e);
}
function Qe(e) {
	if (Xe.length === 0 && !Rt) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function $e() {
	for (; Xe.length > 0;) Ze();
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function et(e) {
	return e === this.v;
}
function tt(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function nt(e) {
	return !tt(e, this.v);
}
// node_modules/svelte/src/internal/client/custom-renderer/state.js
var rt = null;
// node_modules/svelte/src/internal/client/reactivity/async.js
function it(e, t, n, r) {
	var i = V, a = t.map(Ye() ? dt : ht), s = e.filter((e) => !e.settled);
	if (s.length > 0) {
		var c = at(), l = ct();
		(s.length === 1 ? s[0].promise : Promise.all(s.map((e) => e.promise))).then(() => {
			if (!(i.f & 16384)) {
				c(s[0].run.get_batch());
				try {
					u();
				} catch (e) {
					T(e, i);
				}
				ot();
			}
		}).finally(l);
	} else u();
	function u() {
		if (!e.some((e) => e.failed)) {
			if (n.length === 0) r(a);
			else {
				var t = n.map((e) => /* @__PURE__ */ pt(e)), s = null;
				_n(() => {
					for (var e of t) if (mt(e)) {
						J(e);
						return;
					}
					s === null ? s = vn(() => {
						try {
							r([...a, ...t]);
						} catch (e) {
							T(e, i);
						}
					}) : M.revalidate_branch(s);
				}, o);
			}
		}
	}
}
function at() {
	var e = V, t = R, n = E, r = M;
	return function(i = r) {
		H(e), B(t), Ge(n), i !== null && !(e.f & 16384) && D(i).activate();
	};
}
function ot(e = !0) {
	H(null), B(null), Ge(null), e && M?.deactivate();
}
var st = null;
function ct() {
	for (var e = V, t = e.b, n = D(M), r = t; r && !r.is_pending;) r = r.parent;
	return n.increment(e), r?.increment(e, n), t?.update_effect_pending(1), () => {
		D(n).decrement(e), r?.decrement(e, n), t?.update_effect_pending(-1);
	};
}
function D(e) {
	for (; e.merged !== null;) e = e.merged;
	return e;
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var lt = ~(t | n | e);
function O(e, t) {
	e.f = e.f & lt | t;
}
function ut(t) {
	t.f & 512 || t.edges === null ? O(t, e) : O(t, n);
}
/*#__NO_SIDE_EFFECTS__*/
function dt(e) {
	var n = 2 | t;
	return V !== null && (V.f |= s), {
		ctx: E,
		deps: null,
		dv: null,
		edges: null,
		effects: null,
		equals: et,
		f: n,
		fn: e,
		reactions: null,
		rv: 0,
		v: y,
		wv: 0,
		parent: V,
		ac: null
	};
}
var ft = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function pt(e, t, n, r) {
	var i = wt(y);
	i.f |= d;
	var a = /* @__PURE__ */ new Set(), o = st, s = o && M, c = o && [];
	function l(e = !1) {
		var t = c;
		c = e ? null : [], e && (s = null);
		for (let e of t) e();
	}
	return mn(() => {
		var t = V, n = Ae();
		try {
			var u = e();
			if (u === y) return;
			var d = Promise.resolve(u), f = q?.signal;
			d.then((e) => {
				f?.aborted || n.resolve(e);
			}, (e) => {
				f?.aborted || e === ae && o === null || n.reject(e === ae ? ft : e);
			}).finally(ot);
		} catch (e) {
			n.reject(e);
		}
		var p = M, m = ct();
		p.async_deriveds.get(t)?.reject(ft), a.add(n), p.async_deriveds.set(t, n);
		let h = (e, u = void 0) => {
			if (c !== null && u !== ft && (s ??= p, D(p) !== D(s))) c.push(() => {
				var r = !!(t.f & 16384) || (p.linked ? p.async_deriveds.get(t) !== n : !D(p).linked);
				h(e, r ? ft : u);
			});
			else {
				if (m(), a.delete(n), u) {
					if (c !== null && s !== null && (a.size > 0 || u === ft) && D(s) === D(p) && D(p).async_deriveds.get(t) === n) {
						s = null, l();
						return;
					}
					if (u === ft) return;
				}
				var d = i.equals(e) && !u && !(i.f & 8388608);
				D(p).capture(i, u ?? e, d, !!u), o !== null && (o.switch(p), o.continued.push(() => l(!0)), o = null), r?.(u), r = void 0;
			}
		};
		n.promise.then(h, (e) => h(null, e || "unknown"));
	}), sn(() => {
		for (let e of a) e.reject(ft);
	}), i;
}
function mt(e) {
	return (P?.get(e) ?? e).v === y;
}
/*#__NO_SIDE_EFFECTS__*/
function ht(e) {
	let t = /* @__PURE__ */ dt(e);
	return t.equals = nt, t;
}
function gt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) L(t[n]);
	}
}
function _t(e) {
	var t = V, n = e.parent;
	if (!Pn && n !== null && e.v !== y && n.f & 24576) return ce(), ut(e), e.v;
	H(n);
	try {
		return gt(e), ar(e);
	} finally {
		H(t);
	}
}
function vt(e) {
	var t = e;
	if (Yn(t)) {
		var n = F?.records, r = n?.get(t);
		r !== void 0 && Kn(r.deps, r.dv) ? (n.delete(t), fr(t, r)) : _t(t);
	}
}
function yt(e) {
	var t = Ft, n = t.get(e);
	if (n !== void 0) return n;
	var r = F, i = P.get(e), a = i ?? e, o = i === void 0 ? (e.f & m) !== 0 : i.assigned, s = r.get_record(e);
	return o && !qn((s ?? e).deps, a.wv) ? n = a : s !== void 0 && Kn(s.deps, s.dv) ? n = s : i === void 0 && !o && e.dv !== null && Kn(e.deps, e.dv) ? n = e : (_t(e), n = r.records?.get(e) ?? e), e.f & 512 && t.set(e, n), n;
}
function bt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.f & 134217728) && (t.teardown?.(), rr(t), t.fn !== null && (t.teardown = De), _r(t), bn(t));
}
function xt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && vr(t);
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var St = /* @__PURE__ */ new Set(), Ct = !1;
function wt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: et,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Tt(e, t) {
	let n = wt(e, t);
	return Rn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function k(e, t = !1, n = !0) {
	let r = wt(e);
	return t || (r.equals = nt), Ue && n && E !== null && E.l !== null && (E.l.s ??= []).push(r), r;
}
function A(e, t, n = !1) {
	return R !== null && (!z || R.f & 131072) && Ye() && R.f & 4325394 && (U === null || !U.has(e)) && Ve(), Et(e, n ? Er(t) : t, Bt);
}
function Et(e, t, n = null) {
	var r = e.equals(t) && !(e.f & 8388608), i = P?.get(e);
	if (!r || i !== void 0 && (i.e || !e.equals.call(i, t))) {
		var a = Kt.ensure();
		(e.f & 67110914) == 2050 && _t(e), a.capture(e, t, r, !1, n), Ye() && V !== null && V.f & 1024 && !(V.f & 96) && (K === null ? zn([e]) : K.push(e));
	} else Pn && Pt(e);
	return t;
}
function Dt() {
	Ct = !1, tn(Ot);
}
function Ot() {
	for (let e of St) {
		e.f & 1024 && O(e, n);
		let t;
		try {
			t = Yn(e);
		} catch {
			t = !0;
		}
		t && vr(e);
	}
	St.clear();
}
function kt(e) {
	A(e, e.v + 1);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var j = null, At = null, M = null, jt = null, N = null;
function Mt(e) {
	N = e;
}
function Nt(e) {
	var t = N = {
		reverted_values: new Map(N?.reverted_values),
		derived_cache: /* @__PURE__ */ new Map(),
		parent: N
	};
	for (let [n, r] of e ?? []) t.reverted_values.set(n, r);
	return t;
}
function Pt(e) {
	for (var t = N; t !== null; t = t.parent) t.reverted_values.delete(e), t.derived_cache.clear();
}
var P = null, Ft = null, F = null, It = null, Lt = /* @__PURE__ */ new Set(), Rt = !1, zt = null, Bt = null, Vt = 0, Ht = null, Ut = 0, Wt = 1, Gt = null, Kt = class r {
	id = Wt++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	records = null;
	folded = [];
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = null;
	#i = /* @__PURE__ */ new Map();
	#a = [];
	#o = /* @__PURE__ */ new Set();
	#s = /* @__PURE__ */ new Set();
	is_fork = !1;
	merged = null;
	merge_requests = /* @__PURE__ */ new Set();
	#c = !1;
	constructor() {
		At === null ? j = At = this : (At.next = this, this.prev = At), At = this;
	}
	#l() {
		if (this.is_fork) return !0;
		for (let e of this.#n.keys()) if (this.is_blocked_by(e)) return !0;
		return !1;
	}
	#u(e) {
		return this.#o.has(e) || !!(e.f & 33554432) && !this.#s.has(e);
	}
	is_skipped(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#u(t)) return !0;
		return !1;
	}
	is_blocked_by(e, t = null) {
		for (var n = e; n !== null && n !== t; n = n.parent) if (this.#u(n) || (n.f & 16512) == 128 && n.b.is_pending) return !1;
		return !0;
	}
	skip_effect(e) {
		this.#o.add(e), this.#s.delete(e);
	}
	unskip_effect(e) {
		(this.#o.delete(e) || !this.#s.has(e) && (e.f & 33554432 || this.folded.some((t) => t.#o.has(e)))) && this.revalidate_branch(e), this.#s.add(e);
	}
	unskip_new_effect(e) {
		this.#s.add(e);
	}
	revalidate_branch(e) {
		for (var t = e.first; t !== null; t = t.next) {
			var r = t.f;
			!(r & 24576) && !this.#u(t) && (!(r & 131168) && t.fn !== null && this.schedule(t, n), this.revalidate_branch(t));
		}
	}
	#d() {
		var t = [];
		for (let a of this.#a) if (!(a.f & 16384 || !(a.f & 6144))) {
			for (var n = a, r = !1; n.parent !== null;) {
				n = n.parent;
				var i = n.f;
				if (i & 96) {
					if (!(i & 1024)) {
						r = !0;
						break;
					}
					n.f ^= e;
				}
			}
			r || t.push(n);
		}
		return this.#a = [], t;
	}
	#f() {
		if (M = jt = this, N?.derived_cache.clear(), this.started = !0, Gt = this.id, this.#i.size > 0) {
			for (let [e, t] of this.#i) this.#S(e, t);
			this.#i.clear();
		}
		this.activate();
		for (var e = zt = [], t = [], i = [], a = Bt = []; this.#a.length > 0;) {
			Vt++ > 1e3 && (this.#T(), Jt());
			for (let n of this.#d()) try {
				this.#m(n, e, t, i);
			} catch (e) {
				throw nn(n, !0), this.#l() || this.discard(), e;
			}
			if (this.#a.length > 0) {
				for (let e of t) this.#a.push(e);
				for (let t of e) this.#a.push(t);
				t.length = 0, e.length = 0;
			}
		}
		if (M = null, a.length > 0) {
			var o = r.ensure();
			for (let e of a) e.f & 1024 || o.schedule(e, n);
		}
		if (zt = null, Bt = null, this.merge_requests.size > 0) {
			let n = Array.from(this.merge_requests, D).filter((e) => e !== this && e.linked && !e.is_fork).sort((e, t) => e.id - t.id);
			if (this.merge_requests.clear(), n.length > 0) {
				this.#y(t), this.#y(e);
				for (var s = this, c = n.length; c--;) {
					var l = n[c];
					l !== s && (l.#_(s), s = l);
				}
				s.#f();
				return;
			}
		}
		if (this.#l()) {
			this.#y(t), this.#y(e);
			for (let e of this.#o) nn(e);
			a.length > 0 && M.#f();
			return;
		}
		let u = this.#h();
		if (u) this.#y(t), this.#y(e), u.#_(this), u.#f();
		else {
			for (let t of i) t.is_pending && t.is_ready(this) && t.reveal(e);
			this.#C(!0), this.#x(this.#e), Qt(e, Qt(t)), this.#r?.resolve();
			var d = M;
			if (this.#n.size === 0 && (this.#a.length === 0 || d !== null) && this.#T(), d !== null) {
				if (N !== null) for (let [e, t] of N.reverted_values) d.previous.get(e)?.wv !== t.wv && N.reverted_values.delete(e);
				d.#f();
			}
		}
	}
	#p(e) {
		var t = new Set(e), r = /* @__PURE__ */ new Set();
		for (let e of t) {
			var i = e.reactions;
			if (i !== null) for (let e of i) {
				var a = e.f;
				if (a & 2) a & 1024 && O(e, n), t.add(e);
				else {
					var o = e;
					r.has(o) || (r.add(o), !(a & 155648) && !this.is_skipped(o) && this.schedule(o, n));
				}
			}
		}
	}
	#m(t, n, r, i) {
		t.f ^= e;
		for (var a = t.first; a !== null;) {
			var o = a.f, s = !!(o & 96);
			if (!(s && o & 1024 || o & 139264 || this.#u(a)) && a.fn !== null) {
				s ? a.f ^= e : o & 4 ? n.push(a) : Yn(a) && vr(a);
				var c = a.first;
				if (c !== null) {
					a = c;
					continue;
				}
			}
			for (; a !== null;) {
				if ((a.f & 16512) == 128) {
					var l = a.b;
					l.is_pending && l.is_ready(this) && i.push(l);
				}
				var u = a.next;
				if (u !== null) {
					a = u;
					break;
				}
				a = a.parent;
			}
		}
	}
	#h() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#g(e)) return e;
		return null;
	}
	#g(e) {
		for (let t of this.current.keys()) if (e.current.has(t)) return !0;
		return !1;
	}
	#_(e) {
		for (let t of e.merge_requests) this.merge_requests.add(t);
		e.merge_requests.clear();
		for (let [t, n] of e.current) {
			if (!this.previous.has(t)) {
				let n = e.previous.get(t);
				n && this.previous.set(t, n);
			}
			this.current.set(t, n);
		}
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && e !== n && n.promise.then(e.resolve, e.reject), this.async_deriveds.set(t, n);
		}
		for (let [n, r] of e.records ?? []) if (!(n.f & 16)) {
			var t = this.records?.get(n);
			(this.records ??= /* @__PURE__ */ new Map()).set(n, r), e.records?.delete(n), Qn(n, t);
		}
		if (e.async_deriveds.clear(), e.#n.size > 0) {
			for (let [t, n] of e.#n) this.#n.set(t, (this.#n.get(t) ?? 0) + n);
			e.#n.clear();
		}
		if (e.#i.size > 0) {
			for (let [t, n] of e.#i) this.#v(t, n);
			e.#i.clear();
		}
		let n = () => e.discard();
		this.oncommit(n), this.ondiscard(n), e.merged = this, e.#T();
	}
	#v(e, t) {
		(t === 2048 || this.#i.get(e) !== 2048) && this.#i.set(e, t);
	}
	#y(r) {
		for (var i = 0; i < r.length; i += 1) {
			var a = r[i], o = a.f & (t | n);
			o !== 0 && (this.#v(a, a.dv === null ? n : o), O(a, e));
		}
	}
	capture(e, n, r, i = !1, a = null) {
		var o = this.previous.get(e), s = $t(this, e);
		o === void 0 && (o = s?.previous.get(e), o === void 0 && e.v !== y && (o = {
			v: e.v,
			wv: e.wv,
			e: (e.f & f) !== 0,
			assigned: (e.f & m) !== 0
		}), o !== void 0 && this.previous.set(e, o)), Pn ? Pt(e) : o !== void 0 && (N?.reverted_values.set(e, o), N?.derived_cache.clear());
		var c = {
			v: n,
			wv: r ? e.wv : Wn(),
			e: i,
			assigned: !!(e.f & 2),
			async: (e.f & d) !== 0
		};
		this.current.set(e, c), P?.set(e, c), Ft?.delete(e), !this.is_fork && s !== null && s.previous.set(e, c), !this.is_fork && !r && s === null && en(e, c), r || (Ht = null, Ut = 0, this.mark(e, t, a), Ht = null, St.size > 0 && !Ct && Dt());
	}
	deactivate() {
		M = jt = P = Ft = F = null;
	}
	flush() {
		var e = Nt(this.previous);
		try {
			if (this.#f(), Lt.size > 0) for (let e of Lt) Lt.delete(e), e.linked && !e.#c && e.#f();
		} finally {
			Vt = 0, It = null, zt = null, Bt = null, N = e.parent, this.deactivate();
		}
	}
	discard() {
		this.#x(this.#t);
		for (let e of this.async_deriveds.values()) e.reject(ft);
		this.#T(), this.#r?.resolve();
	}
	#b() {
		for (let i = j; i !== null; i = i.next) if (i !== this) {
			var e = i.id < this.id, t = [];
			for (let [r, a] of this.current) {
				var n = i.current.get(r);
				if (n !== void 0) {
					if (e && a.v !== n.v && !n.async) i.current.set(r, a);
					else continue;
				}
				t.push(r);
			}
			if (i.started && i.current.size !== 0) {
				var r = !0;
				for (let e of i.current.keys()) if (!this.current.has(e)) {
					r = !1;
					break;
				}
				r && e ? i.discard() : t.length > 0 && (i.#p(t), Lt.add(i));
			}
		}
		this.current.clear(), this.previous.clear();
	}
	commit_writes() {
		this.#b(), this.linked && this.prev !== null && this.#w();
	}
	increment(e) {
		var t = this.#n.get(e) ?? 0;
		this.#n.set(e, t + 1);
	}
	decrement(e) {
		var t = this.#n.get(e) ?? 0;
		t === 1 ? this.#n.delete(e) : this.#n.set(e, t - 1), this.#c || (this.#c = !0, Qe(() => {
			this.#c = !1, this.linked && this.flush();
		}));
	}
	oncommit(e) {
		this.#e.set(e, Xt?.size ? Xt : null);
	}
	ondiscard(e) {
		this.#t.set(e, Xt?.size ? Xt : null);
	}
	#x(e) {
		Y(() => {
			for (let [n, r] of e) if (r === null) n(this);
			else {
				var t = Nt();
				for (let [e, n] of r) t.reverted_values.has(e) && t.reverted_values.set(e, n);
				try {
					n(this);
				} finally {
					N = t.parent;
				}
			}
		}), e.clear();
	}
	settled() {
		return (this.#r ??= Ae()).promise;
	}
	static ensure() {
		if (M === null) {
			let e = M = new r();
			jt === null && !Rt && Qe(() => {
				e.started || e.flush();
			});
		}
		return M;
	}
	activate() {
		M = this, F = this, Gt !== this.id && (Gt = null), P = Ft = null;
	}
	get_record(e) {
		for (var t = this.records?.get(e), n = this.folded.length; t === void 0 && n--;) t = this.folded[n].records?.get(e);
		return t;
	}
	mark(e, r, i = null) {
		var a = e.reactions;
		if (a !== null) {
			var o = Ye(), s = a.length;
			if (Ut += s, Ut > 1e5 && Ht === null && (Ht = /* @__PURE__ */ new Set()), Ht !== null) {
				if (Ht.has(e)) return;
				Ht.add(e);
			}
			for (var c = 0; c < s; c++) {
				var l = a[c], u = l.f;
				if (o || l !== V) {
					var d = (u & t) === 0;
					if (u & 131072) this.is_fork || (d && O(l, r), St.add(l));
					else if (u & 2) {
						d && O(l, r);
						var f = l;
						Ft?.delete(f), this.mark(f, n, i);
					} else if (d) {
						var p = l;
						u & 16 && Yt !== null && (O(p, r), Yt.add(p)), i === null ? this.schedule(p, r) : (O(p, r), i.push(p));
					}
				}
			}
		}
	}
	schedule(e, t) {
		if (It = e, F !== null && F !== this && e !== R) this.#v(e, e.f & 2097152 ? t : n);
		else {
			if (jt !== this && R === null) {
				if (this.prev !== null || this.next !== null || this.is_fork) {
					this.#v(e, n);
					return;
				}
				t = n;
			}
			this.#S(e, t);
		}
	}
	#S(e, t) {
		e.f & 2048 || O(e, t), this.#a.push(e);
	}
	#C(e = !1) {
		var t = this.records;
		if (t !== null) {
			this.records = null;
			for (let [r, i] of t) {
				if (!(r.f & 16386)) {
					var n = !!(r.f & 4194304) && tr(i) && !tr(r);
					if (e && !n && (fr(r, i), r.f & 4194304)) for (let e = j; e !== null; e = e.next) e !== this && !e.records?.has(r) && e.async_deriveds.get(r)?.reject(ft);
					mr(r);
				}
				Qn(r, i);
			}
		}
	}
	#w() {
		var e = this.prev, t = j;
		e.next = this.next, this.next === null ? At = e : this.next.prev = e, this.prev = null, this.next = t, t.prev = j = this, this.id = t.id - 1;
	}
	#T() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null ? j = t : e.next = t, t === null ? At = e : t.prev = e, this.linked = !1, this.#C();
		}
	}
};
function qt(e) {
	var t = Rt, n = F === M ? null : F;
	Rt = !0;
	try {
		var r;
		for (e && (qt(), r = e());;) {
			if ($e(), M === null) return r;
			M.flush();
		}
	} finally {
		Rt = t, F = n;
	}
}
function Jt() {
	try {
		Ie();
	} catch (e) {
		T(e, It);
	}
}
var Yt = null, Xt = null;
function Zt(e) {
	if ((e.f & 32772) != 4) return !1;
	for (var t = e.b; t !== null; t = t.parent) if (t.is_pending) return t.defer_effect(e), !0;
	return !1;
}
function Qt(e, t = null) {
	var n = e.length;
	if (n === 0) return t;
	for (var r = 0; r < n;) {
		var i = e[r++];
		if (!(i.f & 24576) && !M?.is_skipped(i) && !Zt(i) && Yn(i)) {
			Yt = /* @__PURE__ */ new Set();
			var a = Bn;
			if (vr(i), i.edges === null && i.first === null && i.nodes === null && i.teardown === null && i.ac === null && Cn(i), Yt?.size > 0) {
				var o = N;
				t !== null && Nt(t);
				var s = Xt;
				Xt = new Map(t);
				try {
					for (let e of Yt) {
						if (e.f & 24576 || M?.is_skipped(e)) continue;
						let t = [e], n = e.parent;
						for (; n !== null;) Yt.has(n) && (Yt.delete(n), t.push(n)), n = n.parent;
						for (let e = t.length - 1; e >= 0; e--) {
							let n = t[e];
							n.f & 24576 || M?.is_skipped(n) || vr(n);
						}
					}
				} finally {
					Xt = s, Yt?.clear(), N = o;
				}
			}
			if (Bn !== a && M !== null) for (let [e, n] of M.current) n.wv > a && (t ??= /* @__PURE__ */ new Map()).set(e, n);
		}
	}
	return Yt = null, t;
}
function $t(e, t) {
	for (var n = e.next; n !== null && (n.is_fork || !n.current.has(t));) n = n.next;
	return n;
}
function en(e, t) {
	e.v = t.v, e.wv = t.wv, e.f = t.e ? e.f | f : e.f & ~f, e.f & 2 && (e.f |= m, ut(e));
}
function tn(e) {
	var t = P, n = Ft, r = F;
	P = Ft = F = null;
	try {
		e();
	} finally {
		P = t, Ft = n, F = r;
	}
}
function nn(t, n = !1) {
	if (!(!n && t.f & 32 && t.f & 1024)) {
		O(t, e);
		for (var r = t.first; r !== null;) nn(r, n), r = r.next;
	}
}
// node_modules/svelte/src/internal/client/reactivity/effects.js
function rn(e) {
	V === null && (R === null && Fe(e), Pe()), Pn && Ne(e);
}
function an(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function I(e, n) {
	var i = V;
	i !== null && i.f & 8192 && (e |= r);
	var a = {
		ctx: E,
		deps: null,
		dv: null,
		edges: null,
		nodes: null,
		f: e | t | 512,
		first: null,
		fn: n,
		last: null,
		next: null,
		parent: i,
		b: i && i.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null,
		r: rt
	}, s = a;
	if (e & 4) zt === null ? Kt.ensure().schedule(a, t) : zt.push(a);
	else if (n !== null) {
		try {
			vr(a);
		} catch (e) {
			throw L(a), e;
		}
		s.edges === null && s.teardown === null && s.nodes === null && s.first === s.last && !(s.f & 524288) && (s = s.first, e & 16 && e & 65536 && s !== null && (s.f |= o));
	}
	if (s !== null && (s.parent = i, i !== null && an(s, i), R !== null && R.f & 2 && !(e & 64))) {
		var c = R;
		(c.effects ??= []).push(s);
	}
	return a;
}
function on() {
	return R !== null && !z;
}
function sn(t) {
	let n = I(8, null);
	return O(n, e), n.teardown = t, n;
}
function cn(e) {
	rn("$effect");
	var t = V.f;
	if (!R && t & 32 && E !== null && !E.i) {
		var n = E;
		(n.e ??= []).push(e);
	} else return ln(e);
}
function ln(e) {
	return I(4 | c, e);
}
function un(e) {
	return rn("$effect.pre"), I(8 | c, e);
}
function dn(e) {
	Kt.ensure();
	let t = I(64 | s, e);
	return () => {
		L(t);
	};
}
function fn(e) {
	Kt.ensure();
	let t = I(64 | s, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? wn(t, () => {
			L(t), n(void 0);
		}) : (L(t), n(void 0));
	});
}
function pn(e) {
	return I(4, e);
}
function mn(e) {
	return I(d | s, e);
}
function hn(e, t = 0) {
	return I(8 | t, e);
}
function gn(e, t = [], n = [], r = []) {
	it(r, t, n, (t) => {
		I(8, () => {
			e(...t.map(J));
		});
	});
}
function _n(e, t = 0) {
	return I(16 | t, e);
}
function vn(e) {
	return I(32 | s, e);
}
function yn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Pn, r = Fn, i = N, a = R;
		In(!0), B(null);
		try {
			t.call(null);
		} catch (t) {
			T(t, e.parent);
		} finally {
			In(n, r), Mt(i), B(a);
		}
	}
}
function bn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		rr(n);
		var r = n.next;
		n.f & 64 ? n.parent = null : L(n, t), n = r;
	}
}
function xn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || L(t), t = n;
	}
}
function L(e, t = !0) {
	var n = !1;
	try {
		(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Sn(e.nodes.start, e.nodes.end), n = !0), e.f |= a, bn(e, t && !n), _r(e);
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) e.stop();
		yn(e);
	} finally {}
	e.f ^= a, e.f |= 16384;
	var i = e.parent;
	i !== null && i.first !== null && Cn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.dv = e.edges = e.fn = e.nodes = e.ac = e.b = e.r = null;
}
function Sn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ Pr(e);
		Zr(e), e = n;
	}
}
function Cn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function wn(e, t, n = !0) {
	var r = [];
	e.f |= 256, Tn(e, r, !0);
	var i = () => {
		n && L(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = N, s = () => {
			if (!--a) {
				var e = N;
				try {
					o && (o.derived_cache.clear(), Mt(o)), i();
				} finally {
					o && Mt(e);
				}
			}
		};
		for (var c of r) c.out(s);
	} else i();
}
function Tn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= r;
		var i = e.nodes && e.nodes.t;
		if (i !== null) for (let e of i) (e.is_global || n) && t.push(e);
		for (var a = e.first; a !== null;) {
			var o = a.next;
			if (!(a.f & 64)) {
				var s = !!(a.f & 65536) || !!(a.f & 32) && !!(e.f & 16);
				Tn(a, t, s ? n : !1);
			}
			a = o;
		}
	}
}
function En(e) {
	e.f &= -257, Dn(e, !0);
}
function Dn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= r, e.f & 1024 || Kt.ensure().schedule(e, n);
		for (var i = e.first; i !== null;) {
			var a = i.next, o = !!(i.f & 65536) || !!(i.f & 32);
			Dn(i, o ? t : !1), i = a;
		}
		var s = e.nodes && e.nodes.t;
		if (s !== null) for (let e of s) (e.is_global || t) && e.in();
	}
}
function On(e, t) {
	if (e.nodes) try {
		for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
			var i = n === r ? null : /* @__PURE__ */ Pr(n);
			Jr(t, n), n = i;
		}
	} finally {}
}
// node_modules/svelte/src/internal/client/legacy.js
var kn = null, An = !1;
function jn() {
	An || (An = !0, li(document, "reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ie]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function Mn(e) {
	var t = R, n = V;
	B(null), H(null);
	try {
		return e();
	} finally {
		B(t), H(n);
	}
}
function Nn(e, t, n, r = n) {
	e.addEventListener(t, () => Mn(n));
	let i = e[ie];
	e[ie] = i ? () => {
		i(), r(!0);
	} : () => r(!0), jn();
}
// node_modules/svelte/src/internal/client/runtime.js
var Pn = !1, Fn = 0;
function In(e, t = Bn) {
	Pn = e, Fn = t;
}
var Ln = {
	v: void 0,
	wv: 0,
	e: !1,
	assigned: !1
}, R = null, z = !1;
function B(e) {
	R = e;
}
var V = null;
function H(e) {
	V = e;
}
var U = null;
function Rn(e) {
	R !== null && (R.f & 2097152 || R.f & 2) && (U ??= /* @__PURE__ */ new Set()).add(e);
}
var W = null, G = 0, K = null;
function zn(e) {
	K = e;
}
var Bn = 1, Vn = 0, Hn = Vn;
function Un(e) {
	Hn = e;
}
function Wn() {
	return ++Bn;
}
function Gn(e) {
	return P === null ? (vt(e), e.wv) : e.f & 2 ? yt(e).wv : (P.get(e) ?? e).wv;
}
function Kn(e, t) {
	if (e !== null) {
		for (var n = 0; n < t.length; n++) if (Gn(e[n]) !== t[n]) return !1;
	}
	return !0;
}
function qn(e, t, n = null) {
	if (e !== null) for (var r = 0; r < e.length; r++) {
		var i = e[r];
		if (i.f & 2) {
			var a = i;
			if (P === null ? vt(i) : a = yt(i), a.wv > t) {
				if (a === i ? i.f & 67108864 : !("dv" in a)) return !0;
				if (n === null) n = /* @__PURE__ */ new Set();
				else if (n.has(a)) continue;
				if (qn(a.deps, t, n)) return !0;
				n.add(a);
			}
		} else if (Gn(i) > t) return !0;
	}
	return !1;
}
function Jn(e) {
	return !!(e.f & 4194320) && F?.get_record(e) || e;
}
function Yn(t) {
	var n = t.f;
	if (!(n & 6144)) return !1;
	if (n & 67108864) {
		if (qn(t.deps, t.wv)) return !0;
	} else if (n & 2048) return !0;
	else {
		var r = Jn(t), i = r.deps, a = r.dv;
		if (a === null) return !0;
		if (P === null) for (var o = 0, s = a.length; o < s; o++) {
			var c = i[o];
			if (vt(c), c.wv !== a[o]) return !0;
		}
		else if (!Kn(i, a)) return !0;
	}
	return n & 512 && O(t, e), !1;
}
function Xn(e, r, i = !0) {
	var a = e.reactions;
	if (a !== null && !(U !== null && U.has(e))) for (var o = 0; o < a.length; o++) {
		var s = a[o];
		s.f & 2 ? Xn(s, r, !1) : r === s && M.schedule(s, i ? t : n);
	}
}
var q = null;
function Zn(e) {
	e && Mn(() => e.abort(ae));
}
function Qn(e, t, n = !1) {
	if (t?.ac) {
		for (var r = j; r !== null; r = r.next) if (r.records?.get(e) === t && (!n || r !== F && !nr(M, r))) return;
		Zn(t.ac), t.ac = null;
	}
}
function $n(e, t) {
	var n = M, r = !!(t & 2);
	if (!(r && Pn)) {
		var i = n === null || !n.is_fork;
		Qn(e, F?.records?.get(e), !0), (r ? P === null || i && tr(e) : i) && Zn(e.ac);
		for (var a = j; a !== null; a = a.next) nr(n, a) && Qn(e, a.records?.get(e), !0);
	}
}
function er(e) {
	Zn(e.ac), e.ac = q;
}
function tr({ deps: e, dv: t }) {
	return t === null || t.some((t, n) => e[n].wv !== t);
}
function nr(e, t) {
	return e !== null && !e.is_fork && !t.is_fork && t.id < e.id && (P === null || t.previous.size === 0 || e.folded.includes(t));
}
function rr(e) {
	if (!(e.f & 134217728)) return !1;
	e.f ^= p, Zn(e.ac), e.ac = null;
	for (var t = j; t !== null; t = t.next) {
		var n = t.records?.get(e);
		n?.ac && (Zn(n.ac), n.ac = null);
	}
	return !0;
}
function ir(e) {
	return !(e & 4194304) && (e & 32784) != 32784 ? !1 : F !== null && F === M;
}
function ar(e) {
	let t = M;
	var n = W, r = G, a = K, o = R, s = U, c = E, l = z, d = Hn, f = e.f;
	W = null, G = 0, K = null, R = f & 96 ? null : e, U = null, Ge(e.ctx), z = !1, Hn = ++Vn;
	var p = q;
	q = null, f & 134217728 && $n(e, f);
	try {
		e.f |= u;
		var m = e.fn, h = m();
		if (e.f |= i, or(e, f, h, !1), Ye() && K !== null && !z && (W !== null || G > 0) && !(e.f & 6146)) for (var g = 0; g < K.length; g++) Xn(K[g], e);
		if (o !== null && o !== e) {
			if (Vn++, o.deps !== null) for (let e = 0; e < r; e += 1) o.deps[e].rv = Vn;
			if (n !== null) for (let e of n) e.rv = Vn;
			K !== null && (a === null ? a = K : a.push(...K));
		}
		return h;
	} catch (t) {
		var ee = t;
		try {
			ee = je(t);
		} finally {
			or(e, f, ee, ee === t);
		}
		return ee;
	} finally {
		var _ = q?.signal;
		t !== null && _ !== void 0 && _.addEventListener("abort", () => {
			if (M !== null) {
				let e = D(t);
				e !== M && e.linked && !e.is_fork && M.merge_requests.add(e);
			}
		}), e.f ^= u, W = n, G = r, K = a, R = o, U = s, Ge(c), z = l, Hn = d, q = p;
	}
}
function or(e, t, n, r) {
	var i = e.deps, a = G + (W === null ? 0 : W.length), o = e.dv;
	if (e.f & 16384) Zn(q);
	else if (q !== null && !(e.f & 134217728) && (Zn(q), q = null), t & 2 && Pn) {
		for (var s = 0, c = 0; c < a; c++) {
			var l = c < G ? i[c] : W[c - G];
			s = Math.max(s, Cr(l));
		}
		Ln = {
			v: n,
			wv: s,
			e: r,
			assigned: (t & m) !== 0
		};
	} else if (t & 2 && P === null && j !== null && j.next !== null && lr(e, t), W === null && P === null && o !== null && a === i?.length && e.edges === i && !(t & 4194320)) {
		for (var u = 0; u < a; u++) o[u] = i[u].wv;
		o.length !== a && (o.length = a), t & 2 && sr(e, n, r), (e.ac || q) && er(e);
	} else cr(e, t, a, n, r);
}
function sr(e, t, n) {
	var r = e.f & ~m;
	(n || r & 8388608 || !e.equals(t)) && (e.v = t, e.wv = Wn(), r = n ? r | f : r & ~f), e.f = r, ut(e);
}
function cr(e, t, n, r, i) {
	var a = ir(t);
	if (P !== null && t & 2) {
		var o = P.get(e);
		o !== void 0 && o.wv !== e.wv && (a = !0);
	}
	var s = e.deps, c = s;
	(W !== null || G !== s?.length) && (c = G === 0 ? W : s.slice(0, G).concat(W ?? []));
	for (var l = !a && P === null && e.dv !== null ? e.dv : [], u = 0; u < n; u++) {
		var d = c[u];
		l[u] = ur(d), P !== null && t & 2 && (l[u] !== d.wv || (d.f & 1026) == 2) && (a = !0);
	}
	l.length !== n && (l.length = n), !a && P !== null && t & 2 && lr(e, t);
	var f = a || pr(e), p = on() && !!(e.f & 512), m = e.edges;
	if (f && m !== null) {
		if (W !== null) {
			e.edges = m = m.slice();
			for (d of W) _e.call(m, d) || (m.push(d), p && (d.reactions ??= []).push(e));
		}
	} else {
		if (m === s) {
			if (m !== null) for (u = G; u < m.length; u++) gr(e, m[u]);
			if (p && W !== null) for (d of W) (d.reactions ??= []).push(e);
		} else {
			var h = new Set(c);
			for (d of m) h.delete(d) || gr(e, d);
			if (p) for (d of h) (d.reactions ??= []).push(e);
		}
		e.edges = c;
	}
	if (a) {
		var g = F;
		(g.records ??= /* @__PURE__ */ new Map()).set(e, t & 2 ? {
			deps: c,
			dv: l,
			v: r,
			e: i,
			wv: dr(e, g, r, i),
			ac: q
		} : {
			deps: c,
			dv: l,
			ac: q
		});
	} else e.deps = c, e.dv = l, (e.ac || q) && er(e), t & 2 && (sr(e, r, i), F?.records?.delete(e));
}
function lr(e, t) {
	var n = e.dv;
	if (!(n === null || n.length === 0 || t & 67108864)) {
		for (var r, i = e.ac, a = i !== null && M !== null && M.is_fork && !i.signal.aborted, o = j; o !== null; o = o.next) o !== F && !o.records?.has(e) && (i === null || a || nr(M, o)) && (r ??= {
			deps: e.deps,
			dv: n.slice(),
			v: e.v,
			wv: e.wv,
			e: (t & f) !== 0
		}, (o.records ??= /* @__PURE__ */ new Map()).set(e, r));
		a && r !== void 0 && (r.ac = i, e.ac = null);
	}
}
function ur(e) {
	return P === null ? e.wv : e.f & 2 ? Ft.get(e)?.wv ?? -1 : (P.get(e) ?? e).wv;
}
function dr(e, t, n, r) {
	if (!r) {
		var i = t.get_record(e);
		if (i !== void 0 && !i.e && e.equals.call(i, n)) return i.wv;
		if (!(e.f & 8388608) && e.equals(n)) return e.wv;
	}
	return Wn();
}
function fr(e, t) {
	if (e.deps = t.deps, e.dv = e.f & 2 ? t.dv.slice() : t.dv, e.f & 2) {
		var n = e;
		n.v = t.v, n.wv = t.wv, n.f = (t.e ? n.f | f : n.f & ~f) & ~m, ut(n);
	}
	Zn(e.ac), e.ac = t.ac ?? null, t.ac = null;
}
function pr(e) {
	for (var t = j; t !== null; t = t.next) if (t.records?.has(e)) return !0;
	return !1;
}
function mr(e) {
	var t = e.edges, n = e.deps;
	if (!(t === n || pr(e))) {
		for (var r of t) n !== null && _e.call(n, r) || gr(e, r);
		e.edges = n;
	}
}
function hr(e, t) {
	var n = e.reactions ??= [];
	_e.call(n, t) || n.push(t);
}
function gr(e, n) {
	let r = n.reactions;
	if (r !== null) {
		var i = ge.call(r, e);
		if (i !== -1) {
			var a = r.length - 1;
			a === 0 ? r = n.reactions = null : (r[i] = r[a], r.pop());
		}
	}
	if (r === null && n.f & 2 && (W === null || !_e.call(W, n))) {
		var o = n;
		if (o.f & 512 && (o.f ^= 512), o.v !== y && ut(o), rr(o)) {
			O(o, t), o.dv = null;
			for (var s = j; s !== null; s = s.next) s.records?.delete(o);
			Ft?.delete(o);
		}
		bt(o), _r(o);
	}
}
function _r(e) {
	var t = e.edges;
	if (t !== null) for (var n = 0; n < t.length; n++) gr(e, t[n]);
}
function vr(t) {
	var n = t.f;
	if (!(n & 16384)) {
		O(t, e);
		var r = V;
		V = t;
		try {
			n & 16777232 ? xn(t) : bn(t), yn(t);
			var i = ar(t);
			t.teardown = typeof i == "function" ? i : null, t.wv = Bn;
		} finally {
			V = r;
		}
	}
}
async function yr() {
	await Promise.resolve(), qt();
}
function J(e) {
	var t = !!(e.f & 2);
	kn?.add(e);
	var n = null;
	if (R !== null && !z && !(V !== null && V.f & 16384) && (U === null || !U.has(e))) {
		var r = R.deps;
		if (R.f & 2097152) e.rv < Vn && (e.rv = Vn, W === null && r !== null && r[G] === e ? G++ : W === null ? W = [e] : W.push(e));
		else {
			n = R;
			var a = R.edges;
			a !== null && _e.call(a, e) || (R.edges = a === null ? [e] : [...a, e]), hr(e, R);
		}
	}
	if (Pn) {
		var o = Sr(e);
		if (o !== void 0) {
			if (o.e) throw o.v;
			return o.v;
		}
	}
	var s;
	if (t) {
		var c = e, l = !(c.f & 512) && !z && R !== null && !!(R.f & 512), u = !(c.f & i);
		l && (c.f |= 512), P === null ? vt(c) : s = yt(c), l && !u && (xt(c), xr(c));
	} else P !== null && (s = P.get(e));
	if (n !== null && br(n, e, s === void 0 ? e.wv : s.wv), s !== void 0 && s !== e) {
		if (s.e) throw s.v;
		return s.v;
	}
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function br(e, t, n) {
	var r = Jn(e), i = r.deps;
	r.dv === null || i !== null && _e.call(i, t) || (r.deps = i === null ? [t] : [...i, t], r.dv.push(n));
}
function xr(e) {
	if (e.f |= 512, e.edges !== null) for (let t of e.edges) hr(t, e), t.f & 2 && !(t.f & 512) && (xt(t), xr(t));
}
function Sr(e) {
	var t = e.wv > Fn ? void 0 : N?.reverted_values.get(e);
	if (!(e.f & 2)) return t;
	var n = e, r = (N ?? Nt()).derived_cache, i = r.get(n);
	if (i !== void 0) return i;
	var a = t ?? P?.get(n), o = a === void 0 ? (n.f & m) !== 0 : a.assigned, s = a === void 0 && !o ? n.dv : null, c = n.deps ?? [], l = o || s !== null, u = s?.length ?? c.length;
	a ??= {
		v: n.v,
		wv: n.wv,
		e: (n.f & f) !== 0,
		assigned: (n.f & m) !== 0
	};
	for (var d = 0; l && d < u; d++) {
		var p = Cr(c[d]);
		l = s === null ? p <= a.wv : p === s[d];
	}
	return l ? i = a : (_t(n), i = Ln, a.wv < i.wv && !a.e && !i.e && n.equals.call(a, i.v) && (i.wv = a.wv)), r.set(n, i), i;
}
function Cr(e) {
	return (Sr(e) ?? P?.get(e) ?? e).wv;
}
function Y(e) {
	var t = z;
	try {
		return z = !0, e();
	} finally {
		z = t;
	}
}
function wr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (h in e) Tr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && h in n && Tr(n);
		}
	}
}
function Tr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Tr(e[n], t);
		} catch {}
		let n = Te(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = Se(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
function Er(e) {
	if (typeof e != "object" || !e || h in e || g in e) return e;
	let t = Te(e);
	if (t !== Ce && t !== we) return e;
	var n = /* @__PURE__ */ new Map(), r = he(e), i = /* @__PURE__ */ Tt(0), a = null, o = Hn, s = (e) => {
		if (Hn === o) return e();
		var t = R, n = Hn;
		B(null), Un(o);
		var r = e();
		return B(t), Un(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Tt(e.length, a)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || ze();
			var i = n.get(t);
			return i === void 0 ? s(() => {
				var e = /* @__PURE__ */ Tt(r.value, a);
				return n.set(t, e), e;
			}) : A(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = s(() => /* @__PURE__ */ Tt(y, a));
					n.set(t, e), kt(i);
				}
			} else A(r, y), kt(i);
			return !0;
		},
		get(t, r, i) {
			if (r === h) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || xe(t, r)?.writable) && (o = s(() => /* @__PURE__ */ Tt(Er(c ? t[r] : y), a)), n.set(r, o)), o !== void 0) {
				var l = J(o);
				return l === y ? void 0 : l;
			}
			return Reflect.get(t, r, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var r = Reflect.getOwnPropertyDescriptor(e, t), i = n.get(t);
			if (i !== void 0) {
				var a = J(i);
				if (a === y) return;
				if (r && "value" in r) r.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === h) return !0;
			var r = n.get(t), i = r !== void 0 && r.v !== y || Reflect.has(e, t);
			return (r !== void 0 || (V !== null || R !== null) && (!i || xe(e, t)?.writable)) && (r === void 0 && (r = s(() => /* @__PURE__ */ Tt(i ? Er(e[t]) : y, a)), n.set(t, r)), J(r) === y) ? !1 : i;
		},
		set(e, t, o, c) {
			var l = n.get(t), u = t in e;
			if (r && t === "length") for (var d = o; d < l.v; d += 1) {
				var f = n.get(d + "");
				f === void 0 ? d in e && (f = s(() => /* @__PURE__ */ Tt(y, a)), n.set(d + "", f)) : A(f, y);
			}
			if (l === void 0) (!u || xe(e, t)?.writable) && (l = s(() => /* @__PURE__ */ Tt(void 0, a)), A(l, Er(o)), n.set(t, l));
			else {
				u = l.v !== y;
				var p = s(() => Er(o));
				A(l, p);
			}
			var m = Reflect.getOwnPropertyDescriptor(e, t);
			if (m?.set && m.set.call(c, o), !u) {
				if (r && typeof t == "string") {
					var h = n.get("length"), g = Number(t);
					Number.isInteger(g) && g >= h.v && A(h, g + 1);
				}
				kt(i);
			}
			return !0;
		},
		ownKeys(e) {
			J(i);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== y;
			});
			for (var [r, a] of n) a.v !== y && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Be();
		}
	});
}
var Dr, Or, kr, Ar;
function jr() {
	if (Dr === void 0) {
		Dr = window, Or = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		kr = xe(t, "firstChild").get, Ar = xe(t, "nextSibling").get, Ee(e) && (e[v] = void 0, e[te] = null, e[ne] = void 0, e.__e = void 0), Ee(n) && (n[re] = void 0);
	}
}
function Mr(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Nr(e) {
	return kr.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Pr(e) {
	return Ar.call(e);
}
function X(e, t) {
	if (!b) return /* @__PURE__ */ Nr(e);
	var n = /* @__PURE__ */ Nr(S);
	if (n === null) n = Jr(S, Mr());
	else if (t && Wr(n) !== 3) {
		var r = Mr();
		return Yr(n, r), C(r), r;
	}
	return t && Hr(n), C(n), n;
}
function Fr(e, t = !1) {
	if (!b) {
		var n = /* @__PURE__ */ Nr(e);
		return Ur(n) && ti(n) === "" ? /* @__PURE__ */ Pr(n) : n;
	}
	if (t) {
		if (Wr(S) !== 3) {
			var r = Mr();
			return S && Yr(S, r), C(r), r;
		}
		Hr(S);
	}
	return S;
}
function Ir(e, t = !1) {
	if (!b) return /* @__PURE__ */ Nr(e);
	var n = X(e, t);
	return w(e), n;
}
function Z(e, t = 1, n = !1) {
	let r = b ? S : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ Pr(r);
	if (!b) return r;
	if (n) {
		if (Wr(r) !== 3) {
			var a = Mr();
			return r === null ? i && Xr(i, a) : Yr(r, a), C(a), a;
		}
		Hr(r);
	}
	return C(r), r;
}
function Lr(e) {
	e.textContent = "";
}
function Rr() {
	return Xt !== null && !!(V.f & i);
}
function zr(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function Br() {
	return document.createDocumentFragment();
}
function Vr(e, t, n = "") {
	if (t.startsWith("xlink:")) e.setAttributeNS("http://www.w3.org/1999/xlink", t, n);
	else return e.setAttribute(t, n);
}
function Hr(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && Wr(t) === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Ur(e) {
	return e instanceof Comment;
}
function Wr(e) {
	if (e != null) return e.nodeType;
}
function Gr(e) {
	return e.nodeName;
}
function Kr(e) {
	return e.lastChild;
}
function qr(e) {
	return e.parentNode;
}
function Jr(e, t) {
	return e.appendChild(t);
}
function Yr(e, t) {
	e.before(t);
}
function Xr(e, t) {
	e.after(t);
}
function Zr(e) {
	e.remove();
}
function Qr(e, t) {
	return e.removeChild(t);
}
function $r(e, t) {
	e.textContent = t;
}
function ei(e, t) {
	e.nodeValue = t;
}
function ti(e) {
	return e.nodeValue;
}
function ni(e, t) {
	e.value = t ?? "";
}
function ri(e, t) {
	return e.getAttribute(t);
}
function ii(e, t) {
	e.removeAttribute(t);
}
function ai(e, t) {
	return e.hasAttribute(t);
}
function oi(e, t) {
	e.innerHTML = t;
}
function si(e, t) {
	return e.cloneNode(t);
}
function ci(e, t) {
	return document.importNode(e, t);
}
function li(e, t, n, r) {
	e.addEventListener(t, n, r);
}
function ui(e, t, n, r) {
	e.removeEventListener(t, n, r);
}
function di(e, t, n) {
	e.classList.toggle(t, n);
}
// node_modules/svelte/src/internal/flags/legacy.js
jr(), typeof window < "u" && ((globalThis.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5"), We(), [.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var fi = ["touchstart", "touchmove"];
function pi(e) {
	return fi.includes(e);
}
// node_modules/svelte/src/internal/client/dom/elements/events.js
var mi = Symbol("events"), hi = Symbol("propagation stopped at"), gi = /* @__PURE__ */ new Set(), _i = /* @__PURE__ */ new Set();
function vi(e, t, n, r = {}) {
	var i = rt != null;
	function a(...e) {
		if (i) return Mn(() => n?.apply(this, e));
		var a = e[0];
		if (r.capture || wi.call(t, a), r.capture || a[hi] !== t) return Mn(() => n?.call(this, a));
	}
	return !i && (e.startsWith("pointer") || e.startsWith("touch") || e === "wheel") ? (a.__removed = !1, Qe(() => {
		a.__removed || li(t, e, a, r);
	})) : li(t, e, a, r), a;
}
function yi(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = vi(e, t, n, a);
	rt == null && (t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && sn(() => {
		o.__removed = !0, ui(t, e, o, a);
	});
}
var bi = /* @__PURE__ */ new Map();
function xi(e) {
	var t = /* @__PURE__ */ new Set(), n = (n) => {
		for (var r = 0; r < n.length; r++) {
			var i = n[r];
			if (!t.has(i)) {
				t.add(i);
				var a = pi(i);
				for (let t of [e, document]) {
					var o = bi.get(t);
					o === void 0 && (o = /* @__PURE__ */ new Map(), bi.set(t, o));
					var s = o.get(i);
					s === void 0 ? (t.addEventListener(i, wi, { passive: a }), o.set(i, 1)) : o.set(i, s + 1);
				}
			}
		}
	};
	return n(ve(gi)), _i.add(n), () => {
		for (var r of t) for (let t of [e, document]) {
			var i = bi.get(t), a = i.get(r);
			--a == 0 ? (t.removeEventListener(r, wi), i.delete(r), i.size === 0 && bi.delete(t)) : i.set(r, a);
		}
		_i.delete(n);
	};
}
var Si = null, Ci = !1;
function wi(e) {
	var t = this, n = e.cancelBubble;
	if (!(n && e[hi] === t)) {
		n || delete e[hi];
		var r = t.ownerDocument, i = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
		Si = e, Ci || (Ci = !0, setTimeout(() => {
			Ci = !1, Si = null;
		}));
		var s = 0, c = Si === e && e[mi];
		if (c) {
			var l = a.indexOf(c);
			if (l !== -1 && (t === document || t === window)) {
				e[mi] = t;
				return;
			}
			var u = a.indexOf(t);
			if (u === -1) return;
			l <= u && (s = l);
		}
		if (o = a[s] || e.target, o !== t) {
			be(e, "currentTarget", {
				configurable: !0,
				get() {
					return o || r;
				}
			});
			var d = R, f = V;
			B(null), H(null);
			try {
				for (var p, m = []; o !== null && o !== t;) {
					try {
						var h = o[mi]?.[i];
						h == null || o.disabled && e.target !== o || h.call(o, e);
					} catch (e) {
						p ? m.push(e) : p = e;
					}
					if (e.cancelBubble) {
						n || (e[hi] = t);
						break;
					}
					s++, o = s < a.length ? a[s] : null;
				}
				if (p) {
					for (let e of m) queueMicrotask(() => {
						throw e;
					});
					throw p;
				}
			} finally {
				e[mi] = t, delete e.currentTarget, B(d), H(f);
			}
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var Ti = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Ei(e) {
	return Ti?.createHTML(e) ?? e;
}
function Di(e) {
	var t = zr("template");
	return oi(t, Ei(e.replaceAll("<!>", "<!---->"))), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function Oi(e, t) {
	var n = V;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (b) return Oi(S, null), S;
		i === void 0 && (i = Di(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Nr(i)));
		var t = r || Or ? ci(i, !0) : si(i, !0);
		return n ? Oi(/* @__PURE__ */ Nr(t), Kr(t)) : Oi(t, t), t;
	};
}
function $(e, t) {
	if (b) {
		var n = V;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = S), de();
	} else e !== null && Yr(e, t);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function ki(e) {
	let t = 0, n = wt(0), r;
	return () => {
		on() && (J(n), hn(() => (t === 0 && (r = Y(() => e(() => kt(n)))), t += 1, () => {
			Qe(() => {
				--t, t === 0 && (r?.(), r = void 0, kt(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ai = o | s;
function ji(e, t, n, r) {
	new Mi(e, t, n, r);
}
var Mi = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = b ? S : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = !1;
	#d = [];
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = ki(() => (this.#p = wt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = V;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = V.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = _n(() => {
			if (b) {
				let e = me(this.#t);
				de();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, Ai), b && (this.#e = S);
	}
	#h() {
		try {
			this.#a = vn(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		Qe(r), t && (this.#s = vn(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? ue() : (t = !0, n && He(), this.#s !== null && wn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					T(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return !!(this.#i.f & 33570816);
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = vn(() => e(this.#e)), Qe(() => {
			if (!this.#v()) try {
				var e = this.#c = Br(), t = Mr();
				Jr(e, t), this.#a = this.#x(() => {
					try {
						return vn(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e);
						} catch (e) {
							T(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a !== null && this.#f.size === 0 && (this.is_pending = !1, Yr(this.#e, e), this.#c = null, wn(this.#o, () => {
					this.#o = null;
				}));
			} finally {}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#l = 0, this.#a = vn(() => {
				this.#r(this.#e);
			}), this.#f.size === 0) this.is_pending = !1;
			else {
				let t = this.#n.pending;
				if (t) {
					var e = this.#c = Br();
					On(this.#a, e), this.#o = vn(() => t(this.#e));
				}
			}
		} catch (e) {
			this.error(e);
		}
	}
	defer_effect(e) {
		this.#d.push(e);
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = V, n = R, r = E;
		H(this.#i), B(this.#i), Ge(this.#i.ctx);
		try {
			return Kt.ensure(), e();
		} finally {
			H(t), B(n), Ge(r);
		}
	}
	is_ready(e) {
		if (e.is_fork && this.#f.size > 0) return !1;
		for (let [t, n] of this.#f) if (!t.is_fork) {
			for (let t of n.keys()) if (e.is_blocked_by(t, this.#a)) return !1;
		}
		return !0;
	}
	reveal(e) {
		this.is_pending = !1;
		for (let n of this.#d) O(n, t), e.push(n);
		if (this.#d.length = 0, this.#o && wn(this.#o, () => {
			this.#o = null;
		}), this.#c) try {
			Yr(this.#e, this.#c), this.#c = null;
		} finally {}
	}
	increment(e, t) {
		var n = this.#f.get(t);
		n === void 0 && this.#f.set(t, n = /* @__PURE__ */ new Map());
		var r = n.get(e) ?? 0;
		n.set(e, r + 1);
	}
	decrement(e, t) {
		var r = this.#f.get(t), i = r.get(e);
		i === 1 ? (r.delete(e), r.size === 0 && this.#f.delete(t), Qe(() => {
			this.is_pending && !this.#v() && Kt.ensure().schedule(this.#i, n);
		})) : r.set(e, i - 1);
	}
	update_effect_pending(e) {
		this.#l += e, !this.#p || this.#u || (this.#u = !0, Qe(() => {
			this.#u = !1, this.#p && Et(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), J(this.#p);
	}
	error(e) {
		if (e === se || !this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.oncommit(() => {
			this.#v() || this.#S(e);
		})) : this.#S(e);
	}
	#S(e) {
		this.#a &&= (L(this.#a), null), this.#o &&= (L(this.#o), null), this.#s &&= (L(this.#s), null), b && (C(this.#t), fe(), C(pe()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#x(() => {
				try {
					return vn(() => {
						var r = V;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return T(e, this.#i.parent), null;
				}
			}));
		};
		Qe(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					T(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => T(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function Ni(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[re] ??= ti(e)) && (e[re] = n, ei(e, `${n}`));
}
function Pi(e, t) {
	return Ii(e, t);
}
function Fi(e, t) {
	t.intro = t.intro ?? !1;
	let n = t.target, r = b, i = S;
	try {
		for (var a = /* @__PURE__ */ Nr(n); a && (Wr(a) !== 8 || ti(a) !== "[");) a = /* @__PURE__ */ Pr(a);
		if (!a) throw se;
		x(!0), C(a);
		let r = Ii(e, {
			...t,
			anchor: a
		});
		return x(!1), r;
	} catch (r) {
		if (r instanceof Error && r.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw r;
		return r !== se && console.warn("Failed to hydrate: ", r), t.recover === !1 && Le(), Lr(n), x(!1), Pi(e, t);
	} finally {
		x(r), C(i);
	}
}
function Ii(e, t) {
	return Li(e, t);
}
function Li(e, { target: t, anchor: n, props: r = {}, events: i, context: a, intro: o = !0, transformError: s, renderer: c }) {
	var l = void 0, u = fn(() => {
		var o = n ?? Jr(t, Mr());
		ji(o, { pending: () => {} }, (t) => {
			Ke({});
			var n = E;
			if (a && (n.c = a), i && (r.$$events = i), b && Oi(t, null), l = e(t, r) || Je(), b && (V.nodes.end = S, S === null || Wr(S) !== 8 || ti(S) !== "]")) throw le(), se;
			qe();
		}, s);
		var u = c ? null : xi(t);
		return () => {
			if (u?.(), o !== n) {
				var e = qr(o);
				e && Qr(e, o);
			}
		};
	});
	return Ri.set(l, u), l;
}
var Ri = /* @__PURE__ */ new WeakMap();
function zi(e, t) {
	let n = Ri.get(e);
	return n ? (Ri.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Bi = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	#a = null;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t, this.#a = rt;
	}
	#o = (e) => {
		if (this.#e.has(e)) try {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) En(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (En(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), Zr(Kr(r.fragment)), Yr(this.anchor, r.fragment), n = r.effect, n.f &= ~l);
			}
			this.#s(e);
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = Br();
						On(r, t), Jr(t, Mr()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else L(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), wn(r, i, !1)) : i();
			}
		} finally {}
	};
	#s = (e) => {
		for (let t of this.#e.keys()) t !== e && t.linked || this.#e.delete(t);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (L(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = Rr();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = Br(), a = Mr();
				Jr(i, a);
				var o = vn(() => t(a));
				o.f |= l, n.unskip_new_effect(o), this.#n.set(e, {
					effect: o,
					fragment: i
				});
			} else this.#t.set(e, vn(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#o), n.ondiscard(this.#s);
		} else b && (this.anchor = S), this.#o(n);
	}
};
function Vi(e) {
	E === null && Me("onMount"), Ue && E.l !== null ? Hi(E).m.push(e) : cn(() => {
		let t = Y(e);
		if (typeof t == "function") return t;
	});
}
function Hi(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function Ui(e, t, n = !1) {
	var r;
	b && (r = S, de());
	var i = new Bi(e), a = n ? o : 0;
	function s(e, t) {
		if (b) {
			var n = me(r);
			if (e !== parseInt(n.substring(1))) {
				var a = pe();
				C(a), i.anchor = a, x(!1), i.ensure(e, t), x(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	_n(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, s(n, t);
		}), e || s(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/shared/attributes.js
var Wi = [..." 	\n\r\f\xA0\v﻿"];
function Gi(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Wi.includes(r[o - 1])) && (s === r.length || Wi.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
// node_modules/svelte/src/internal/client/dom/css.js
function Ki(e, t) {
	pn(() => {
		e = V?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = zr("style");
			e.id = t.hash, $r(e, t.code), Jr(r, e);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/elements/class.js
function qi(e, t, n, r, i, a) {
	var o = e[v];
	if (b || o !== n || o === void 0) {
		var s = Gi(n, r, a);
		b && s === ri(e, "class") || (s == null ? ii(e, "class") : t ? e.className = s : Vr(e, "class", s)), e[v] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && di(e, c, l);
	}
	return a;
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Ji = Symbol("is custom element"), Yi = Symbol("is html"), Xi = oe ? "link" : "LINK", Zi = oe ? "progress" : "PROGRESS";
function Qi(e) {
	if (b) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, ai(e, "value")) {
					var n = e.value;
					ea(e, "value", null), e.value = n;
				}
				if (ai(e, "checked")) {
					var r = e.checked;
					ea(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ie] = n, Qe(n), jn();
	}
}
function $i(e, t) {
	var n = ta(e);
	n.value !== (n.value = t ?? void 0) && (rt != null || e.value !== t || t === 0 && Gr(e) === Zi) && ni(e, t);
}
function ea(e, t, n, r) {
	var i = ta(e);
	if (!(b && (i[t] = ri(e, t), t === "src" || t === "srcset" || t === "href" && Gr(e) === Xi))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[_] = n), n == null ? ii(e, t) : typeof n != "string" && ra(e).has(t) ? e[t] = n : (!b || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && Vr(e, t, n));
	}
}
function ta(e) {
	return e[te] ??= {
		[Ji]: Gr(e).includes("-"),
		[Yi]: rt == null && e.namespaceURI === "http://www.w3.org/1999/xhtml"
	};
}
var na = /* @__PURE__ */ new Map();
function ra(e) {
	var t = ri(e, "is") || Gr(e), n = na.get(t);
	if (n) return n;
	na.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = Se(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = Te(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ia(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	Nn(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = aa(e) ? oa(a) : a, n(a), M !== null && r.add(M), await yr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (b && e.defaultValue !== e.value || Y(t) == null && e.value) && (n(aa(e) ? oa(e.value) : e.value), M !== null && r.add(M)), hn(() => {
		var n = t();
		e === document.activeElement && r.has(F) || aa(e) && n === oa(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function aa(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function oa(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function sa(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => wr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ dt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => J(i);
	}
	n.b.length && un(() => {
		ca(t, r), ke(n.b);
	}), cn(() => {
		let e = Y(() => n.m.map(Oe));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && cn(() => {
		ca(t, r), ke(n.a);
	});
}
function ca(e, t) {
	if (e.l.s) for (let t of e.l.s) J(t);
	t();
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var la = !1;
function ua(e) {
	var t = la;
	try {
		return la = !1, [e(), la];
	} finally {
		la = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function da(e, t, n, r) {
	var i = !Ue || !!(n & 2), a = !!(n & 8), o = !!(n & 16), s = r, c = !0, l = void 0, u = () => o && i ? (l ??= /* @__PURE__ */ dt(r), J(l)) : (c && (c = !1, s = o ? Y(r) : r), s);
	let d;
	if (a) {
		var f = h in e || ee in e;
		d = xe(e, t)?.set ?? (f && t in e ? (n) => e[t] = n : void 0);
	}
	var p, m = !1;
	a ? [p, m] = ua(() => e[t]) : p = e[t], p === void 0 && r !== void 0 && (p = u(), d && (i && Re(t), d(p)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? u() : (c = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (s = void 0), n === void 0 ? s : n;
	};
	if (i && !(n & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || _ || m) && d(t ? g() : e), e) : g();
		});
	}
	var te = !1, v = (n & 1 ? dt : ht)(() => (te = !1, g()));
	a && J(v);
	var ne = V;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? J(v) : i && a ? Er(e) : e;
			return A(v, n), te = !0, s !== void 0 && (s = n), e;
		}
		return Pn && te || ne.f & 16384 ? v.v : J(v);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function fa(e) {
	return new pa(e);
}
var pa = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ k(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return J(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === ee || (J(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return A(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		}), i = {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		};
		this.#t = e.hydrate ? Fi(e.component, i) : Pi(e.component, i), e?.props?.$$host && e.sync !== !1 || qt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && be(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			zi(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, ma;
typeof HTMLElement == "function" && (ma = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = zr("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = ga(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ha(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = fa({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = dn(() => {
				hn(() => {
					this.$$r = !0;
					for (let e of ye(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ha(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ha(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return ye(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function ha(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function ga(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function _a(e, t, n, r, i, a) {
	let o = class extends ma {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return ye(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return ye(t).forEach((e) => {
		be(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = ha(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (xe(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		be(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
// SlskdCard.svelte
var va = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-11uhbwz\">● Connected</span>"), ya = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-11uhbwz\">⚠ Disconnected</span>"), ba = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-11uhbwz\">● Active</span>"), xa = /* @__PURE__ */ Q("<button class=\"btn-ghost small svelte-11uhbwz\">Activate</button>"), Sa = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11uhbwz\">Loading...</div>"), Ca = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-11uhbwz\"> </button>"), wa = /* @__PURE__ */ Q("<div> </div>"), Ta = /* @__PURE__ */ Q("<div class=\"webhook-details\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Webhook Callback URL</span> <div class=\"copy-input-wrapper svelte-11uhbwz\"><input type=\"text\" readonly=\"\" class=\"input-field readonly svelte-11uhbwz\"/> <button type=\"button\" class=\"btn-copy svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">Add this URL to your slskd configuration to enable real-time\n              ingestion.</span></label> <div class=\"yaml-block svelte-11uhbwz\"><div class=\"yaml-header svelte-11uhbwz\"><span>slskd.yml Integration Config</span> <button type=\"button\" class=\"btn-ghost small svelte-11uhbwz\"> </button></div> <pre class=\"code-block svelte-11uhbwz\"><code> </code></pre></div> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-ghost svelte-11uhbwz\"> </button> <button class=\"btn-ghost svelte-11uhbwz\">Refresh Details</button></div> <!></div>"), Ea = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11uhbwz\">Loading webhook configuration...</div>"), Da = /* @__PURE__ */ Q("<div class=\"settings-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-grid svelte-11uhbwz\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input-field svelte-11uhbwz\"/> <span class=\"helper-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input-field svelte-11uhbwz\"/></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">API Key</span> <div class=\"password-wrapper svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input-field svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-visibility svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div> <div class=\"settings-section webhook-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Webhooks & Automation</h3> <p class=\"section-description svelte-11uhbwz\">Configure slskd to immediately notify EchoSync upon download completion\n        or failure. This enables real-time tag verification, automatic library\n        admission, and immediate daemon transfer eviction.</p> <!></div>", 1), Oa = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"card-title svelte-11uhbwz\">Slskd</h2> <div class=\"badges svelte-11uhbwz\"><span class=\"type-badge svelte-11uhbwz\">Download Client</span> <!> <!></div></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-ghost svelte-11uhbwz\"> </button></div></div> <!></section>"), ka = {
	hash: "svelte-11uhbwz",
	code: ".plugin-card.svelte-11uhbwz {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:16px;}.card-title.svelte-11uhbwz {margin:0;font-size:20px;font-weight:700;}.badges.svelte-11uhbwz {display:flex;gap:8px;}.type-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:700;text-transform:uppercase;}.status-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;}.status-badge.warning.svelte-11uhbwz {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11uhbwz {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.header-right.svelte-11uhbwz {display:flex;gap:8px;}.btn-ghost.svelte-11uhbwz {padding:8px 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.small.svelte-11uhbwz {padding:4px 12px;font-size:11px;font-weight:700;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;}.btn-ghost.svelte-11uhbwz:hover {background:var(--bg-surface-elevated);filter:brightness(1.2);}.btn-primary.svelte-11uhbwz {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz:hover {opacity:0.9;}.loading-state.svelte-11uhbwz {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-11uhbwz {margin-top:16px;}.section-title.svelte-11uhbwz {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-11uhbwz {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-11uhbwz {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11uhbwz {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-11uhbwz {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}.webhook-section.svelte-11uhbwz {border-top:1px solid var(--border-subtle, #1e293b);padding-top:20px;margin-top:24px;}.section-description.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);margin:-8px 0 16px 0;line-height:1.4;}.copy-input-wrapper.svelte-11uhbwz {display:flex;gap:8px;}.input-field.readonly.svelte-11uhbwz {background:rgba(15, 23, 42, 0.6);color:var(--color-primary, #14b8a6);font-family:monospace;font-size:12px;}.btn-copy.svelte-11uhbwz {padding:0 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;transition:all 0.2s;white-space:nowrap;}.btn-copy.svelte-11uhbwz:hover {background:var(--color-primary, #14b8a6);color:#000;}.yaml-block.svelte-11uhbwz {margin-top:12px;background:#090d16;border:1px solid var(--border-subtle, #1e293b);border-radius:8px;overflow:hidden;}.yaml-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(30, 41, 59, 0.4);border-bottom:1px solid var(--border-subtle, #1e293b);font-size:12px;font-weight:600;color:var(--text-secondary, #94a3b8);}.code-block.svelte-11uhbwz {margin:0;padding:12px;font-family:\"JetBrains Mono\", \"Fira Code\", monospace;font-size:12px;color:#38bdf8;overflow-x:auto;white-space:pre;line-height:1.4;}.test-result-banner.svelte-11uhbwz {margin-top:12px;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:500;}.test-result-banner.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;border:1px solid rgba(16, 185, 129, 0.3);}.test-result-banner.error.svelte-11uhbwz {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:1px solid rgba(239, 68, 68, 0.3);}"
};
function Aa(e, t) {
	Ke(t, !1), Ki(e, ka);
	let n = da(t, "apiBase", 12, ""), r = /* @__PURE__ */ k(""), i = /* @__PURE__ */ k(""), a = /* @__PURE__ */ k(""), o = /* @__PURE__ */ k(!1), s = /* @__PURE__ */ k(!0), c = /* @__PURE__ */ k(!1), l = /* @__PURE__ */ k(!1), u = /* @__PURE__ */ k(!1), d = /* @__PURE__ */ k(!1), f = /* @__PURE__ */ k(!1), p = !1, m = /* @__PURE__ */ k(!1), h = /* @__PURE__ */ k(null), g = /* @__PURE__ */ k(!1), ee = /* @__PURE__ */ k(!1), _ = /* @__PURE__ */ k(null), te = /* @__PURE__ */ k(!1), v = /* @__PURE__ */ k(!1);
	Vi(async () => {
		await oe(), await ie(), await ne(), A(s, !1);
	});
	async function ne() {
		try {
			A(g, !0);
			let e = await (await fetch(`${n()}/webhooks/info`)).json();
			e && e.endpoint && A(h, e.endpoint);
		} catch (e) {
			console.error("Failed to load webhook info:", e);
		} finally {
			A(g, !1);
		}
	}
	async function re() {
		try {
			A(ee, !0), A(_, null);
			let e = await fetch(`${n()}/webhooks/test`, { method: "POST" }), t = await e.json();
			e.ok && t.success ? A(_, {
				success: !0,
				message: "Ping successful! Webhook gateway received and dispatched event."
			}) : A(_, {
				success: !1,
				message: t.detail || "Ping failed."
			});
		} catch (e) {
			A(_, {
				success: !1,
				message: `Ping failed: ${e.message}`
			});
		} finally {
			A(ee, !1);
		}
	}
	async function ie() {
		try {
			let e = await (await fetch(`${n()}/download-clients/active`)).json();
			A(m, e.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function ae() {
		try {
			await fetch(`${n()}/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), A(m, !0);
		} catch (e) {
			console.error("Failed to activate client:", e);
		}
	}
	async function oe() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e && (A(r, e.slskd_url || ""), A(a, e.server_name || ""), A(i, e.api_key || ""), A(f, e.has_api_key || !1), A(o, e.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e);
		}
	}
	async function se() {
		if (!J(r).trim()) console.error("Server URL is required");
		else try {
			A(c, !0);
			let e = {
				slskd_url: J(r),
				server_name: J(a)
			};
			J(i) && J(i) !== "****" && (e.api_key = J(i)), await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), await oe();
		} catch (e) {
			console.error("Failed to save slskd settings:", e);
		} finally {
			A(c, !1);
		}
	}
	async function y() {
		if (J(r).trim()) try {
			A(l, !0), (await (await fetch(`${n()}/connection/test`, { method: "POST" })).json())?.success ? (A(o, !0), await oe()) : A(o, !1);
		} catch (e) {
			console.error("Failed to test slskd connection:", e), A(o, !1);
		} finally {
			A(l, !1);
		}
	}
	async function ce() {
		let e = !J(d);
		if (A(d, e), e && J(f) && J(i) === "****" && !p) try {
			let e = await (await fetch(`${n()}/settings/key`)).json();
			e && e.api_key ? (A(i, e.api_key), p = !0) : A(d, !1);
		} catch {
			A(d, !1);
		}
		!e && p && (A(i, "****"), p = !1);
	}
	function le(e, t) {
		navigator?.clipboard && navigator.clipboard.writeText(e).then(() => {
			t === "yaml" ? (A(te, !0), setTimeout(() => A(te, !1), 2e3)) : (A(v, !0), setTimeout(() => A(v, !1), 2e3));
		});
	}
	var ue = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), qt();
		}
	};
	sa();
	var b = Oa(), x = X(b), S = X(x), C = Z(X(S), 2), de = Z(X(C), 2), pe = (e) => {
		$(e, va());
	}, me = (e) => {
		$(e, ya());
	};
	Ui(de, (e) => {
		J(o) ? e(pe) : J(r) && e(me, 1);
	});
	var he = Z(de, 2), ge = (e) => {
		$(e, ba());
	};
	Ui(he, (e) => {
		J(m) && e(ge);
	}), w(C), w(S);
	var _e = Z(S, 2), ve = X(_e), ye = (e) => {
		var t = xa();
		yi("click", t, ae), $(e, t);
	};
	Ui(ve, (e) => {
		!J(m) && J(o) && e(ye);
	});
	var be = Z(ve, 2), xe = Ir(be, !0);
	w(_e), w(x);
	var Se = Z(x, 2), Ce = (e) => {
		$(e, Sa());
	}, we = (e) => {
		var t = Da(), n = Fr(t), o = Z(X(n), 2), s = X(o), u = Z(X(s), 2);
		Qi(u), fe(2), w(s);
		var p = Z(s, 2), m = Z(X(p), 2);
		Qi(m), w(p);
		var ie = Z(p, 2), ae = Z(X(ie), 2), oe = X(ae);
		Qi(oe);
		var ue = Z(oe, 2), b = Ir(ue, !0);
		w(ae), fe(2), w(ie);
		var x = Z(ie, 2), S = X(x), C = Ir(S, !0), de = Z(S, 2), pe = (e) => {
			var t = Ca(), n = Ir(t, !0);
			gn(() => {
				t.disabled = J(l), Ni(n, J(l) ? "Testing..." : "Test Connection");
			}), yi("click", t, y), $(e, t);
		};
		Ui(de, (e) => {
			J(r) && (J(f) || J(i)) && e(pe);
		}), w(x), w(o), w(n);
		var me = Z(n, 2), he = Z(X(me), 4), ge = (e) => {
			var t = Ta(), n = X(t), r = Z(X(n), 2), i = X(r);
			Qi(i);
			var a = Z(i, 2), o = Ir(a, !0);
			w(r), fe(2), w(n);
			var s = Z(n, 2), c = X(s), l = Z(X(c), 2), u = Ir(l, !0);
			w(c);
			var d = Z(c, 2), f = Ir(X(d), !0);
			w(d), w(s);
			var p = Z(s, 2), m = X(p), ie = Ir(m, !0), ae = Z(m, 2);
			w(p);
			var oe = Z(p, 2), se = (e) => {
				var t = wa(), n = Ir(t, !0);
				gn(() => {
					qi(t, 1, `test-result-banner ${J(_), Y(() => J(_).success ? "success" : "error") ?? ""}`, "svelte-11uhbwz"), Ni(n, (J(_), Y(() => J(_).message)));
				}), $(e, t);
			};
			Ui(oe, (e) => {
				J(_) && e(se);
			}), w(t), gn(() => {
				$i(i, (J(h), Y(() => `${J(h).url}${J(h).secret ? "?secret=" + J(h).secret : ""}`))), Ni(o, J(v) ? "Copied!" : "Copy"), Ni(u, J(te) ? "Copied!" : "Copy YAML"), Ni(f, (J(h), Y(() => J(h).yaml_template))), m.disabled = J(ee), Ni(ie, J(ee) ? "Pinging Webhook..." : "Test Webhook Ingress"), ae.disabled = J(g);
			}), yi("click", a, () => le(`${J(h).url}${J(h).secret ? "?secret=" + J(h).secret : ""}`, "url")), yi("click", l, () => le(J(h).yaml_template, "yaml")), yi("click", m, re), yi("click", ae, ne), $(e, t);
		}, _e = (e) => {
			$(e, Ea());
		};
		Ui(he, (e) => {
			J(h) ? e(ge) : e(_e, -1);
		}), w(me), gn(() => {
			ea(oe, "type", J(d) ? "text" : "password"), Ni(b, J(d) ? "🙈" : "👁️"), S.disabled = J(c), Ni(C, J(c) ? "Saving..." : "Save Settings");
		}), ia(u, () => J(r), (e) => A(r, e)), ia(m, () => J(a), (e) => A(a, e)), ia(oe, () => J(i), (e) => A(i, e)), yi("click", ue, ce), yi("click", S, se), $(e, t);
	};
	return Ui(Se, (e) => {
		J(s) ? e(Ce) : J(u) || e(we, 1);
	}), w(b), gn(() => Ni(xe, J(u) ? "Expand" : "Collapse")), yi("click", be, () => A(u, !J(u))), $(e, b), qe(ue);
}
customElements.define("slskd-dashboard-card", _a(Aa, { apiBase: {} }, [], [], { mode: "open" }));
export { Aa as default };
